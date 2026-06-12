from types import SimpleNamespace

from app.prompts.prompts import build_chat_prompt


def create_conversation_chain(llm):
    prompt = build_chat_prompt()

    def predict(conversation_history: str, patient_message: str) -> str:
        messages = prompt.format_messages(
            conversation_history=conversation_history,
            patient_message=patient_message,
        )
        response = llm.invoke(messages)
        return getattr(response, "content", str(response)).strip()

    return SimpleNamespace(predict=predict)
