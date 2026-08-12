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
import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Request
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


# ---------- real booking endpoint (Retell / any agent can call this) ----------

@app.post("/book")
async def book(req: Request):
    """Insert a real HVAC booking row into Supabase. Called as a tool by the agent.
    Reads SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY from the environment.

    Auth: if BOOK_API_SECRET is set, requires a matching `x-api-key` header.
    (If it's unset, the endpoint stays open — fine for local testing, set it for prod.)"""
    secret = os.getenv("BOOK_API_SECRET")
    if secret and req.headers.get("x-api-key") != secret:
        raise HTTPException(status_code=401, detail="unauthorized")

    data = await req.json()
    row = {
        "caller_name": data.get("name") or data.get("caller_name"),
        "address": data.get("address"),
        "problem": data.get("problem"),
        "is_emergency": data.get("is_emergency"),
        "time_preference": data.get("time_preference") or data.get("time"),
        "source": data.get("source") or "retell",
    }

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not (url and key):
        return {"ok": False, "error": "supabase not configured"}

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{url}/rest/v1/hvac_bookings",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",  # ask Supabase to return the new row
            },
            json=row,
        )

    ok = r.status_code < 300
    booking_id = None
    confirmation_code = None
    if ok:
        try:
            created = r.json()
            if isinstance(created, list) and created:
                booking_id = created[0].get("id")
                if booking_id:
                    # short, speakable code (first 6 hex chars of the uuid)
                    confirmation_code = booking_id.replace("-", "")[:6].upper()
        except Exception:
            pass

    return {
        "ok": ok,
        "status": r.status_code,
        "booking_id": booking_id,
        "confirmation_code": confirmation_code,
        "message": (f"Booking saved. Confirmation code {confirmation_code}."
                    if ok else "Booking failed to save."),
    }


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
