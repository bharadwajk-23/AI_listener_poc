import json
from datetime import datetime

from app.services.db import find_summaries, insert_summary
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


def format_history(history: List[Message]) -> str:
    return "\n".join(f"{item.role.capitalize()}: {item.content}" for item in history)


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
    conversation_text = format_history(request.conversation_history)
    try:
        reply = conversation_chain.predict(
            conversation_history=conversation_text,
            patient_message=request.message,
        )
        return ChatResponse(reply=reply.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/summary", response_model=SummaryResponse)
def summary(request: SummaryRequest):
    conversation_text = format_history(request.conversation_history)
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
            doc["conversation_history"] = [
                {"role": m.role, "content": m.content} for m in request.conversation_history
            ]
            doc["stored_at"] = datetime.utcnow().isoformat()
            inserted_id = insert_summary(doc)
            # include an optional id in the returned payload? keep response shape as-is
        except Exception as db_exc:
            # don't fail the request if DB storage fails; just log
            print(f"Warning: failed to store summary in DB: {db_exc}")

        return SummaryResponse(**data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/summaries", response_model=List[SummaryDocument])
def list_summaries():
    try:
        return find_summaries()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
