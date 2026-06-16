from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Message] = []


class ChatResponse(BaseModel):
    reply: str


class SummaryRequest(BaseModel):
    conversation_history: List[Message] = []


class SummaryResponse(BaseModel):
    patient_progress: str
    current_symptoms: List[str]
    pain_level: str
    functional_status: str
    exercise_adherence: str
    medication_concerns: str
    new_symptoms: List[str]
    patient_concerns: List[str]
    clinical_summary: str


class SummaryDocument(BaseModel):
    patient_progress: str
    current_symptoms: List[str]
    pain_level: str
    functional_status: str
    exercise_adherence: str
    medication_concerns: str
    new_symptoms: List[str]
    patient_concerns: List[str]
    clinical_summary: str
    conversation_history: List[Message]
    stored_at: Optional[datetime] = None
