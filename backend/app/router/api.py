import json
from typing import List

from fastapi import APIRouter, HTTPException

from app.schemas.models import (
    ChatRequest,
    ChatResponse,
    Message,
    SummaryRequest,
    SummaryResponse,
)

router = APIRouter()
conversation_chain = None
summary_chain = None


def format_history(history: List[Message]) -> str:
    return "\n".join(f"{item.role.capitalize()}: {item.content}" for item in history)


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
        data = json.loads(raw_summary)
        return SummaryResponse(**data)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Summary generation failed to return valid JSON. Please check the Groq model response.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
