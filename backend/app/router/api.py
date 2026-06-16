import json
import os
import urllib.request
import urllib.error
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

# Get API base URL from environment, default to localhost:8000
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Default session ID (can be made dynamic per user if needed)
DEFAULT_SESSION_ID = "default_session"


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
    # Use backend conversation history instead of frontend's
    backend_history = get_conversation_history(DEFAULT_SESSION_ID)
    
    # Store user message
    store_message(DEFAULT_SESSION_ID, "user", request.message)
    
    # Format history for LLM
    conversation_text = format_history([Message(**msg) for msg in backend_history] + [Message(role="user", content=request.message)])
    
    try:
        reply = conversation_chain.predict(
            conversation_history=conversation_text,
            patient_message=request.message,
        ).strip()
        
        # Store assistant reply
        store_message(DEFAULT_SESSION_ID, "assistant", reply)
        
        chat_ended = is_chat_ended(reply)
        if chat_ended:
            try:
                # Get full conversation history including current exchange
                full_history = get_conversation_history(DEFAULT_SESSION_ID)
                payload = {
                    "conversation_history": full_history
                }
                summary_url = f"{API_BASE_URL}/summary"
                req = urllib.request.Request(
                    summary_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        resp_text = resp.read().decode("utf-8")
                        print(f"Summary triggered, response: {resp.getcode()}")
                except Exception as summary_exc:
                    print(f"Warning: summary HTTP request failed after chat end: {summary_exc}")
            except Exception as summary_exc:
                print(f"Warning: failed to prepare summary request: {summary_exc}")

        return ChatResponse(reply=reply, chat_ended=chat_ended)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/summary", response_model=SummaryResponse)
def summary(request: SummaryRequest):
    # Use backend conversation history instead of request history
    backend_history = get_conversation_history(DEFAULT_SESSION_ID)
    conversation_text = format_history([Message(**msg) for msg in backend_history])
    
    try:
        raw_summary = summary_chain.predict(conversation_history=conversation_text)
        try:
            data = json.loads(raw_summary)
        except json.JSONDecodeError:
            extracted = extract_json_object(raw_summary)
            data = json.loads(extracted)
        data = normalize_summary_data(data)
        # persist summary to MongoDB (best-effort)
        try:
            doc = dict(data)
            doc["conversation_history"] = backend_history
            doc["stored_at"] = datetime.utcnow().isoformat()
            inserted_id = insert_summary(doc)
        except Exception as db_exc:
            print(f"Warning: failed to store summary in DB: {db_exc}")

        # Clear conversation history after storing summary
        clear_conversation(DEFAULT_SESSION_ID)
        
        return SummaryResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/summaries", response_model=List[SummaryDocument])
def list_summaries():
    try:
        return find_summaries()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
