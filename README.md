# Healthcare Conversational AI Demo

A minimal healthcare chat application powered by FastAPI, LangChain, and Groq.

## Features
- Simple patient chat interface
- AI assistant guides follow-up conversation
- Summary generation on conversation end
- Clean HTML/CSS/JavaScript frontend

## Project structure

```
project/
├── backend/
│   ├── main.py
│   ├── llm.py
│   ├── prompts.py
│   ├── conversation_chain.py
│   ├── summary_chain.py
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

## Setup

1. Create a Python virtual environment:

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create a `.env` file in `backend/` with your Groq API key:

```text
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

4. Run the backend:

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

5. Serve the frontend:

```powershell
cd ..\frontend
python -m http.server 8080
```

6. Open your browser at:

```text
http://localhost:8080
```

## Usage

- The page loads with an initial AI greeting.
- Enter updates in the chat box.
- Type `done`, `finish`, or `end conversation` to receive a structured summary.

## Notes

- This app does not use a database, authentication, agents, or memory storage.
- All conversation state is kept in the browser until the session ends.
