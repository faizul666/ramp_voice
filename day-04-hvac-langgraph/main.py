"""
FastAPI wrapper around the HVAC LangGraph state machine.

Two endpoints:
  POST /chat              - simple JSON, for local testing/understanding
  POST /chat/completions  - OpenAI-compatible, for VAPI's custom-LLM integration

Each caller gets a session (keyed by session_id / VAPI call id); every request
advances the state machine by one turn.

Run:  uvicorn main:app --port 8000
"""

import json
import time

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from graph import graph

app = FastAPI(title="HVAC Receptionist")

# In-memory session store: session_id -> graph state (clipboard).
# Fine for dev; a real deploy would use Redis/DB so it survives restarts.
sessions: dict[str, dict] = {}


def advance(session_id: str, message: str) -> dict:
    """Advance one caller turn. Returns the graph state after this turn."""
    state = sessions.get(session_id)
    if state is None:
        # New call: run the greeting turn (advances to identify_problem).
        state = graph.invoke({"step": "greet", "user_input": ""})
        sessions[session_id] = state
        # If the caller already spoke on this first request (VAPI greeted first),
        # process that message too so we don't lose their opening line.
        if message:
            state["user_input"] = message
            state = graph.invoke(state)
            sessions[session_id] = state
        return state
    state["user_input"] = message
    state = graph.invoke(state)
    sessions[session_id] = state
    return state


@app.get("/health")
def health():
    return {"ok": True}


# ---------- simple JSON endpoint (local testing) ----------

class ChatIn(BaseModel):
    session_id: str
    message: str = ""


class ChatOut(BaseModel):
    reply: str
    done: bool


@app.post("/chat", response_model=ChatOut)
def chat(inp: ChatIn) -> ChatOut:
    state = advance(inp.session_id, inp.message)
    return ChatOut(reply=state["reply"], done=bool(state.get("done")))


# ---------- OpenAI-compatible endpoint (VAPI custom-LLM) ----------

def _sse_openai(text: str, model: str = "hvac-langgraph"):
    """Stream `text` back in OpenAI chat.completion.chunk SSE format (what VAPI expects)."""
    created = int(time.time())

    def gen():
        first = {
            "id": "chatcmpl-hvac", "object": "chat.completion.chunk",
            "created": created, "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": text},
                         "finish_reason": None}],
        }
        yield f"data: {json.dumps(first)}\n\n"
        last = {
            "id": "chatcmpl-hvac", "object": "chat.completion.chunk",
            "created": created, "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(last)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/chat/completions")
async def chat_completions(req: Request):
    body = await req.json()
    messages = body.get("messages", [])
    call = body.get("call") or {}

    # VAPI includes the call object; use its id as the session key.
    session_id = call.get("id") or body.get("metadata", {}).get("session_id") or "default"

    # The newest user turn is the last message with role "user".
    user_msgs = [m for m in messages if m.get("role") == "user"]
    last_user = (user_msgs[-1].get("content") if user_msgs else "") or ""

    state = advance(session_id, last_user)
    return _sse_openai(state["reply"])
