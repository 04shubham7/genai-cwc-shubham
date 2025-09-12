from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from persona.engine import PersonaEngine


app = FastAPI(title="Persona Chat API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(payload: Dict[str, str]):
    query = (payload or {}).get("query", "").strip()
    if not query:
        return JSONResponse(status_code=400, content={"error": "query is required"})

    engine = PersonaEngine()
    result = engine.run(query)
    return JSONResponse(content=result)


@app.post("/api/chat/stream")
def chat_stream(payload: Dict[str, str]):
    query = (payload or {}).get("query", "").strip()
    if not query:
        return JSONResponse(status_code=400, content={"error": "query is required"})

    engine = PersonaEngine()

    async def event_stream() -> AsyncGenerator[bytes, None]:
        # Simple Server-Sent Events-like stream (not full SSE headers), suitable for fetch reader.
        for step in engine.step_generator(query):
            chunk = ("data: " + JSONResponse(content=step).body.decode("utf-8") + "\n\n").encode("utf-8")
            yield chunk
            await asyncio.sleep(0)  # cooperative yield

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
