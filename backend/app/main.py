import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.router.api import router
from app.schemas.models import Message
from app.services.llm import get_llm
from app.services.conversation_chain import create_conversation_chain
from app.services.summary_chain import create_summary_chain
import app.router.api as api

app = FastAPI(title="Healthcare Chat Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = get_llm()
conversation_chain = create_conversation_chain(llm)
summary_chain = create_summary_chain(llm)

api.conversation_chain = conversation_chain
api.summary_chain = summary_chain

app.include_router(router)
