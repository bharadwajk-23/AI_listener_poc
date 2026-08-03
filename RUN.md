# Running the App — Backend, Frontend, and Data Flow

This repo is a small healthcare-chat POC: a FastAPI backend (LLM via Groq + MongoDB storage) and a plain HTML/JS frontend chat widget, plus a second static "summary dashboard" served by the backend itself.

## 1. Pieces in this repo

| Piece | Location | Served by |
|---|---|---|
| API backend | `backend/app/` (entry: `app/main.py`) | `uvicorn`, port **8004** |
| Chat frontend (widget) | `frontend/` (`index.html`, `app.js`, `style.css`) | any static server, e.g. port 3000/8080 |
| Summary dashboard | `backend/app/static/` | mounted **by the backend itself** at `/ptmantra/summary_dashboard` |
| Python venv (already created) | `venv/` at repo root | has fastapi, uvicorn, langchain, langchain-groq, pymongo already installed |

There is no separate "frontend build" — both frontends are static files, no npm/node involved.

## 2. One-time setup

### 2.1 Environment variables

Create/check `.env` in the repo root (already `.gitignore`d). It needs:

```
GROQ_API_KEY=your_groq_api_key
MONGODB_URI=your_mongodb_connection_string
API_BASE_URL=http://localhost:8004/ptmantra   # optional, has this default
GROQ_MODEL=llama-3.3-70b-versatile            # optional, this is the default
```

- `GROQ_API_KEY` — required. Without it, `get_llm()` in [llm.py](backend/app/services/llm.py:12) raises on startup.
- `MONGODB_URI` — required. Without it, [db.py](backend/app/services/db.py:19) raises when the backend tries to connect (on startup, via `ensure_collections()`, and on every summary read/write).
- Check the repo-root `.env` already exists — verify the values are filled in before starting the backend.

### 2.2 Python environment

A venv already exists at the repo root (`venv/`, Python 3.12) with all of `backend/requirements.txt` installed. Just activate it:

```powershell
cd "C:\Users\YSI165\Desktop\AI Listener\POC_1\ppoc"
venv\Scripts\activate
```

If you ever need to rebuild it: `pip install -r backend\requirements.txt`.

## 3. Running it

### 3.1 Backend (FastAPI, port 8004)

```powershell
cd "C:\Users\YSI165\Desktop\AI Listener\POC_1\ppoc"
venv\Scripts\activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8004
```

On startup it will:
- Load `.env`, build the Groq LLM client and the conversation/summary chains.
- Call `ensure_collections()` to create/validate the `summaries` Mongo collection (best-effort — logs a warning and continues if Mongo is unreachable).
- Mount the static summary dashboard at `/ptmantra/summary_dashboard`.

Check it's up:
- Swagger docs: http://localhost:8004/ptmantra/docs
- Summary dashboard: http://localhost:8004/ptmantra/summary_dashboard

### 3.2 Chat frontend (static, e.g. port 3000)

In a second terminal:

```powershell
cd "C:\Users\YSI165\Desktop\AI Listener\POC_1\ppoc"
python -m http.server 3000 --directory frontend
```

(This matches the `frontend` config already defined in [.claude/launch.json](.claude/launch.json) — if you're using the Claude Code preview tool, just start that named config instead of running the command by hand.)

Then open **http://localhost:3000**.

`frontend/app.js` is hardcoded to call the backend at `http://localhost:8004/ptmantra/chat` and `/ptmantra/summary` — so the backend must be running on 8004 for the chat UI to work.

### 3.3 Summary dashboard (already served, no separate step needed)

Once the backend is running, open **http://localhost:8004/ptmantra/summary_dashboard** — it lists stored summaries via `GET /ptmantra/summaries`.

⚠️ **Known local-dev issue**: [static/config.js](backend/app/static/config.js:2) hardcodes `API_ENDPOINT` to the production URL `https://ailabs.youngsoft.com/ptmantra/summaries` instead of `http://localhost:8004/ptmantra/summaries`. When running locally, the dashboard page will fetch from production, not your local Mongo data. Point it at `http://localhost:8004/ptmantra/summaries` if you need it to reflect local runs.

### 3.4 Alternative: Docker

```powershell
docker compose up --build
```

This builds `backend/Dockerfile` and runs the backend on port 8004 using the repo-root `.env` (see [docker-compose.yml](docker-compose.yml)). It does **not** serve the `frontend/` folder — you'd still run that separately as in 3.2.

## 4. Request flow (what actually happens on a chat message)

```
Browser (frontend/app.js)
   │  POST /ptmantra/chat  { message, session_id? }
   ▼
FastAPI router (backend/app/router/api.py: chat())
   │  1. Resolve/generate session_id
   │  2. Pull history from in-memory store (services/db.py: _active_conversations dict)
   │  3. Store the new user message
   │  4. If assistant has already asked 3 follow-up questions → hard-stop with CLOSING_MESSAGE
   │     else → conversation_chain.predict(...) calls the Groq LLM for a reply
   │  5. Store assistant reply
   │  6. If reply text matches an "ending" phrase (or hard-stop triggered) → chat_ended = true
   │     and internally call summary(...) right away
   ▼
Response { reply, session_id, chat_ended } → rendered in chat window, spoken via browser TTS
```

When a conversation ends (`chat_ended = true`), the backend automatically:
1. Builds a structured summary via `summary_chain.predict(...)` (Groq LLM, expects JSON back).
2. Normalizes the JSON into `SummaryResponse` fields.
3. Stores it in MongoDB (`insert_summary`) together with the full conversation history.
4. Clears the in-memory session history.

The summary dashboard (`/ptmantra/summary_dashboard`) just calls `GET /ptmantra/summaries`, which reads everything back out of MongoDB.

**Note:** all active conversation state lives in a plain Python dict in memory ([db.py](backend/app/services/db.py:11)) — restarting the backend loses any in-progress (not-yet-summarized) conversations. Only finished, summarized conversations persist, in MongoDB.

## 5. Quick checklist to get everything running

1. Fill in `.env` (`GROQ_API_KEY`, `MONGODB_URI`).
2. `venv\Scripts\activate`
3. `cd backend && uvicorn app.main:app --reload --port 8004`
4. New terminal: `python -m http.server 3000 --directory frontend`
5. Open http://localhost:3000 → chat.
6. Open http://localhost:8004/ptmantra/summary_dashboard → view stored summaries (fix `config.js` endpoint first if testing locally).
