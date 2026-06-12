from langchain_core.prompts.chat import ChatPromptTemplate


def build_chat_prompt():
    system_template = """
You are a compassionate healthcare assistant speaking with a patient who is checking in after their last appointment. Keep the tone warm, respectful, and focused on patient symptoms, pain, function, exercise adherence, medication concerns, new symptoms, and overall progress.
If the patient types done, finish, or end conversation, respond with a closing message and do not ask new follow-up questions.
"""

    human_template = """
Conversation history:
{conversation_history}

Patient message:
{patient_message}
"""

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_template),
            ("human", human_template),
        ]
    )


def build_summary_prompt():
    system_template = """
You are a healthcare assistant that converts patient conversation history into a structured clinical summary. Provide a JSON object with the requested fields.
"""

    human_template = """
Here is the patient conversation history:
{conversation_history}

Create a JSON object with these fields:
- patient_progress
- current_symptoms
- pain_level
- functional_status
- exercise_adherence
- medication_concerns
- new_symptoms
- patient_concerns
- clinical_summary

Use arrays for symptom and concern lists. Return valid JSON only.
"""

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_template),
            ("human", human_template),
        ]
    )
