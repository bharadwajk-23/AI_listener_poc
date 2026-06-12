from types import SimpleNamespace

from app.prompts.prompts import build_summary_prompt


def create_summary_chain(llm):
    prompt = build_summary_prompt()

    def predict(conversation_history: str) -> str:
        messages = prompt.format_messages(conversation_history=conversation_history)
        response = llm.invoke(messages)
        return getattr(response, "content", str(response)).strip()

    return SimpleNamespace(predict=predict)
