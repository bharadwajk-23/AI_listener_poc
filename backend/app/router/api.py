import json
import os
import uuid
from datetime import datetime

from app.services.db import find_summaries, insert_summary, store_message, get_conversation_history, clear_conversation
from typing import List

from fastapi import APIRouter, HTTPException

from app.schemas.models import (
    ChatRequest,
    ChatResponse,
    Message,
    SummaryDocument,
    SummaryRequest,
    SummaryResponse,
)

router = APIRouter()
conversation_chain = None
summary_chain = None

# Get API base URL from environment, default to localhost:8004
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8004/ptmantra")

FOLLOWUP_QUESTION_LIMIT = 3
CLOSING_MESSAGE = (
    "Thank you for sharing this information today. Your responses have been recorded "
    "and will be shared with your care team. We appreciate your time and wish you a smooth recovery."
)


def format_history(history: List[Message]) -> str:
    return "\n".join(f"{item.role.capitalize()}: {item.content}" for item in history)


def is_chat_ended(reply: str) -> bool:
    normalized = reply.lower()
    end_markers = [
        "thank you for taking the time to speak with me today",
        "shared with your care team",
        "we'll be in touch soon",
        "we will be in touch soon",
        "shared with teams",
        "shared with tems",
        "thank you",
        "care team"
    ]
    return any(marker in normalized for marker in end_markers)


def count_assistant_followup_questions(history: List[Message]) -> int:
    """Count assistant questions in history, excluding the initial greeting."""
    assistant_messages = [msg for msg in history if msg.role == "assistant"]
    followup_count = 0
    for index, message in enumerate(assistant_messages):
        followup_count += 1
    print(followup_count)
    return followup_count


def extract_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in text.")

    depth = 0
    for index, char in enumerate(text[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    raise ValueError("No balanced JSON object found in text.")


def normalize_summary_data(data: dict) -> dict:
    string_fields = [
        "patient_progress",
        "pain_level",
        "functional_status",
        "exercise_adherence",
        "medication_concerns",
        "clinical_summary",
    ]
    list_fields = [
        "current_symptoms",
        "new_symptoms",
        "patient_concerns",
    ]

    for field in string_fields:
        if field in data and not isinstance(data[field], str):
            if isinstance(data[field], list):
                data[field] = ", ".join(str(item) for item in data[field])
            else:
                data[field] = str(data[field])

    for field in list_fields:
        if field in data and not isinstance(data[field], list):
            if isinstance(data[field], str):
                data[field] = [data[field]]
            else:
                data[field] = [str(data[field])]

    return data


def build_summary_from_history(history: list) -> dict:
    conversation_text = format_history(
        [Message(**msg) if isinstance(msg, dict) else msg for msg in history]
    )
    raw_summary = summary_chain.predict(conversation_history=conversation_text)
    try:
        data = json.loads(raw_summary)
    except json.JSONDecodeError:
        extracted = extract_json_object(raw_summary)
        data = json.loads(extracted)
    return normalize_summary_data(data)


def store_history_summary(session_id: str, history: list, data: dict) -> None:
    history_records = [msg.dict() if isinstance(msg, Message) else msg for msg in history]
    doc = dict(data)
    doc["conversation_history"] = history_records
    doc["stored_at"] = datetime.utcnow().isoformat()
    insert_summary(doc)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # Use provided session_id or generate a new one for a fresh conversation
    session_id = request.session_id or str(uuid.uuid4())

    backend_history = get_conversation_history(session_id)
    followup_questions = count_assistant_followup_questions([Message(**msg) for msg in backend_history])

    store_message(session_id, "user", request.message)

    if followup_questions >= FOLLOWUP_QUESTION_LIMIT:
        print("hard stop")
        reply = CLOSING_MESSAGE
        store_message(session_id, "assistant", reply)
        chat_ended = True
        try:
            full_history = get_conversation_history(session_id)
            summary_request = SummaryRequest(
                session_id=session_id,
                conversation_history=full_history,
            )
            summary(summary_request)
        except Exception as summary_exc:
            print(f"Warning: summary generation failed after chat end: {summary_exc}")

        return ChatResponse(reply=reply, session_id=session_id, chat_ended=chat_ended)

    conversation_text = format_history([Message(**msg) for msg in backend_history] + [Message(role="user", content=request.message)])

    try:
        reply = conversation_chain.predict(
            conversation_history=conversation_text,
            patient_message=request.message,
        ).strip()

        store_message(session_id, "assistant", reply)

        chat_ended = is_chat_ended(reply)
        if chat_ended:
            try:
                full_history = get_conversation_history(session_id)
                summary_request = SummaryRequest(
                    session_id=session_id,
                    conversation_history=full_history
                )
                summary(summary_request)
            except Exception as summary_exc:
                print(f"Warning: summary generation failed after chat end: {summary_exc}")

        return ChatResponse(reply=reply, session_id=session_id, chat_ended=chat_ended)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/summary", response_model=SummaryResponse)
def summary(request: SummaryRequest):
    history = request.conversation_history or get_conversation_history(request.session_id)
    history_records = [msg.dict() if isinstance(msg, Message) else msg for msg in history]

    try:
        data = build_summary_from_history(history_records)
        try:
            store_history_summary(request.session_id, history_records, data)
        except Exception as db_exc:
            print(f"Warning: failed to store summary in DB: {db_exc}")
        clear_conversation(request.session_id)
        print("stored in db and removed in session")

        return SummaryResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/summaries", response_model=List[SummaryDocument])
def list_summaries():
    try:
        return find_summaries()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
