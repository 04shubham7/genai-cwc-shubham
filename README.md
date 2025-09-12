# Persona Chat (FastAPI + Minimal Frontend)

This adds a small FastAPI backend exposing your persona CoT flow and a minimal web UI that visualizes steps similar to your screenshot.

## Prerequisites
- Python 3.11+ (you have 3.13 in venv)
- `GOOGLE_API_KEY` in a `.env` file at repo root

```
GOOGLE_API_KEY=your_key_here
```

## Install
```
# With your venv activated
pip install -r requirements.txt
```

## Run the API
```
python -m uvicorn api.main:app --reload --port 8000
```
- Health: http://localhost:8000/healthz
- Chat (batch): POST http://localhost:8000/api/chat {"query":"..."}
- Chat (stream): POST http://localhost:8000/api/chat/stream {"query":"..."}

## Try the frontend
Just open `frontend/index.html` in your browser. It calls `http://localhost:8000`.

> If your browser blocks mixed content or CORS, ensure the API is running on localhost:8000 (we enabled permissive CORS).

## How it works
- `persona/engine.py` contains a `PersonaEngine` that:
  - Enforces strict JSON steps: analyse → think → output → validate → result
  - Limits repeated content and think streaks
  - Provides a generator to stream steps
- `api/main.py` wraps the engine into synchronous and streaming endpoints
- `frontend/index.html` is a small static UI that renders each step card

## Deploy hints
- Backend: Docker + Render/Cloud Run/Fly.io
- Frontend: Vercel/Netlify or any static host; set API URL env and enable HTTPS

## Security
- Keep `GOOGLE_API_KEY` server-side only; the static frontend talks to your API.