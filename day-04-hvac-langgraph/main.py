"""
FastAPI wrapper around the HVAC LangGraph state machine.

Gives the graph a URL. Each caller gets a session (keyed by session_id); every
request advances the state machine by one turn. This is the plain-JSON version
for local testing/understanding — the VAPI custom-LLM shim comes next.

Run:  uvicorn main:app --reload --port 8000
Test: POST /chat  {"session_id": "abc", "message": "my furnace died"}
"""

from fastapi import FastAPI
from pydantic import BaseModel

from graph import graph

app = FastAPI(title="HVAC Receptionist")

# In-memory session store: session_id -> graph state (clipboard).
# Fine for dev; a real deploy would use Redis/DB so it survives restarts.
sessions: dict[str, dict] = {}


class ChatIn(BaseModel):
    session_id: str
    message: str = ""


class ChatOut(BaseModel):
    reply: str
    done: bool


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat", response_model=ChatOut)
def chat(inp: ChatIn) -> ChatOut:
    state = sessions.get(inp.session_id)

    if state is None:
        # New call: run the greeting turn first (ignores any message on this hit).
        state = graph.invoke({"step": "greet", "user_input": ""})
    else:
        # Existing call: feed the caller's message and advance one turn.
        state["user_input"] = inp.message
        state = graph.invoke(state)

    sessions[inp.session_id] = state
    return ChatOut(reply=state["reply"], done=bool(state.get("done")))
