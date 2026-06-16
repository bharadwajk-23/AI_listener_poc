import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.router.api import router
from app.schemas.models import Message
from app.services.llm import get_llm
from app.services.conversation_chain import create_conversation_chain
from app.services.summary_chain import create_summary_chain
import app.router.api as api
from app.services.db import ensure_collections

app = FastAPI(title="Healthcare Chat Assistant")

# load environment variables from .env for local development
load_dotenv()

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

# Ensure MongoDB collections and validators are present (best-effort)
try:
    ensure_collections()
    print("Db Collections ensured successfully")
except Exception as exc:
    print(f"Warning: ensure_collections failed: {exc}")

app.include_router(router)
