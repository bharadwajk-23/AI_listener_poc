import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def get_llm():
    api_key = ""
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is required.")

    model_name = os.getenv("llama-3.3-70b-versatile", "llama-3.3-70b-versatile")
    return ChatGroq(model=model_name, temperature=0.3, api_key=api_key)
