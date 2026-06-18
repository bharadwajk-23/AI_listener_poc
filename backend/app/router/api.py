import json
import os
import urllib.request
import urllib.error
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


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # Use provided session_id or generate a new one for a fresh conversation
    session_id = request.session_id or str(uuid.uuid4())

    backend_history = get_conversation_history(session_id)

    store_message(session_id, "user", request.message)

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
                payload = {
                    "session_id": session_id,
                    "conversation_history": full_history,
                }
                summary_url = f"{API_BASE_URL}/summary"
                req = urllib.request.Request(
                    summary_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        print(f"Summary triggered, response: {resp.getcode()}")
                except Exception as summary_exc:
                    print(f"Warning: summary HTTP request failed after chat end: {summary_exc}")
            except Exception as summary_exc:
                print(f"Warning: failed to prepare summary request: {summary_exc}")

        return ChatResponse(reply=reply, session_id=session_id, chat_ended=chat_ended)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/summary", response_model=SummaryResponse)
def summary(request: SummaryRequest):
    backend_history = get_conversation_history(request.session_id)
    conversation_text = format_history([Message(**msg) for msg in backend_history])

    try:
        raw_summary = summary_chain.predict(conversation_history=conversation_text)
        try:
            data = json.loads(raw_summary)
        except json.JSONDecodeError:
            extracted = extract_json_object(raw_summary)
            data = json.loads(extracted)
        data = normalize_summary_data(data)
        try:
            doc = dict(data)
            doc["conversation_history"] = backend_history
            doc["stored_at"] = datetime.utcnow().isoformat()
            insert_summary(doc)
        except Exception as db_exc:
            print(f"Warning: failed to store summary in DB: {db_exc}")

        clear_conversation(request.session_id)

        return SummaryResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/summaries", response_model=List[SummaryDocument])
def list_summaries():
    try:
        return find_summaries()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
