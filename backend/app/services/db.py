import os
from datetime import datetime
from pymongo import MongoClient, errors
from typing import Any
from app.schemas.models import SummaryDocument

_client = None

# In-memory session storage for active conversations
# Key: session_id, Value: list of message dicts {"role": ..., "content": ...}
_active_conversations = {}


def get_client():
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError("MONGODB_URI environment variable is not set")
        _client = MongoClient(uri)
    return _client


def get_db():
    client = get_client()
    db_name = os.getenv("MONGODB_DB", "ai_listener")
    return client[db_name]


def get_summaries_collection():
    db = get_db()
    coll_name = os.getenv("MONGODB_SUMMARIES_COLLECTION", "summaries")
    return db[coll_name]


def _summary_json_schema() -> dict:
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "patient_progress",
                "current_symptoms",
                "pain_level",
                "functional_status",
                "exercise_adherence",
                "medication_concerns",
                "new_symptoms",
                "patient_concerns",
                "clinical_summary",
                "conversation_history",
                "stored_at",
            ],
            "properties": {
                "patient_progress": {"bsonType": "string"},
                "current_symptoms": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"},
                },
                "pain_level": {"bsonType": "string"},
                "functional_status": {"bsonType": "string"},
                "exercise_adherence": {"bsonType": "string"},
                "medication_concerns": {"bsonType": "string"},
                "new_symptoms": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"},
                },
                "patient_concerns": {
                    "bsonType": "array",
                    "items": {"bsonType": "string"},
                },
                "clinical_summary": {"bsonType": "string"},
                "conversation_history": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": ["role", "content"],
                        "properties": {
                            "role": {"bsonType": "string"},
                            "content": {"bsonType": "string"},
                        },
                    },
                },
                "stored_at": {"bsonType": "date"},
            },
        }
    }


def ensure_collections():
    db = get_db()
    coll_name = os.getenv("MONGODB_SUMMARIES_COLLECTION", "summaries")
    validator = _summary_json_schema()
    if coll_name not in db.list_collection_names():
        try:
            db.create_collection(coll_name, validator=validator, validationLevel="moderate", validationAction="error")
        except Exception as exc:
            # Some Atlas tiers may not allow certain options; create without validator as fallback
            try:
                db.create_collection(coll_name)
            except Exception:
                pass
    else:
        # attempt to update validator on existing collection
        try:
            db.command(
                "collMod",
                coll_name,
                validator=validator,
                validationLevel="moderate",
                validationAction="error",
            )
        except Exception:
            # ignore failures to modify existing collection validator
            pass


def find_summaries(limit: int = 0, sort_field: str = "stored_at", sort_direction: int = -1) -> list[dict]:
    coll = get_summaries_collection()
    cursor = coll.find({}).sort(sort_field, sort_direction)
    if limit > 0:
        cursor = cursor.limit(limit)
    summaries = []
    for doc in cursor:
        doc.pop("_id", None)
        summaries.append(doc)
    return summaries


def insert_summary(doc: dict) -> str:
    # validate with Pydantic model before inserting
    try:
        # convert stored_at to datetime if it's an ISO string
        if "stored_at" in doc and isinstance(doc["stored_at"], str):
            try:
                doc["stored_at"] = datetime.fromisoformat(doc["stored_at"])
            except Exception:
                doc["stored_at"] = datetime.utcnow()

        summary = SummaryDocument(**doc)
    except Exception as exc:
        raise ValueError(f"Summary document validation failed: {exc}")

    coll = get_summaries_collection()
    # ensure stored_at exists
    if summary.stored_at is None:
        summary.stored_at = datetime.utcnow()

    # insert
    try:
        result = coll.insert_one(summary.dict())
        return str(result.inserted_id)
    except errors.PyMongoError as e:
        raise


# Session-based conversation storage functions
def store_message(session_id: str, role: str, content: str) -> None:
    """Store a message in the active conversation for a session."""
    if session_id not in _active_conversations:
        _active_conversations[session_id] = []
    _active_conversations[session_id].append({"role": role, "content": content})


def get_conversation_history(session_id: str) -> list[dict]:
    """Retrieve the conversation history for a session."""
    return _active_conversations.get(session_id, [])


def clear_conversation(session_id: str) -> None:
    """Clear the conversation history for a session."""
    if session_id in _active_conversations:
        del _active_conversations[session_id]
