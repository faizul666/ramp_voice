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

# Call ids that have already booked, so a completed call books exactly once.
_booked_sessions: set[str] = set()


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

async def _send_sms(to: str | None, body: str) -> dict:
    """Best-effort Twilio message. Returns a status dict; never raises, so a texting
    problem can't fail a booking. No-ops cleanly if Twilio env vars are missing.

    Channel: if TWILIO_WHATSAPP_FROM is set (e.g. 'whatsapp:+14155238886') it sends
    over WhatsApp — the only channel that reaches a Bangladesh number on a trial.
    Otherwise it falls back to plain SMS via TWILIO_FROM_NUMBER.

    Env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and one of
         TWILIO_WHATSAPP_FROM (WhatsApp) / TWILIO_FROM_NUMBER (SMS).
    """
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    wa_from = os.getenv("TWILIO_WHATSAPP_FROM")   # WhatsApp takes priority if set
    sms_from = os.getenv("TWILIO_FROM_NUMBER")

    if wa_from:
        from_num = wa_from
        to_addr = to if (to or "").startswith("whatsapp:") else f"whatsapp:{to}"
    else:
        from_num = sms_from
        to_addr = to

    if not (sid and token and from_num and to):
        return {"sent": False, "reason": "twilio not configured or no recipient"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                auth=(sid, token),
                data={"To": to_addr, "From": from_num, "Body": body},
            )
        if r.status_code < 300:
            return {"sent": True, "sid": r.json().get("sid")}
        # Twilio returns a helpful JSON error (e.g. code 21608 = unverified number
        # on trial, 21612 = geo-permission blocked). Surface it for debugging.
        return {"sent": False, "reason": f"twilio {r.status_code}", "detail": r.text[:300]}
    except Exception as e:
        return {"sent": False, "reason": str(e)[:200]}


def _as_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "1", "emergency", "urgent")
    return bool(v)


async def save_booking(fields: dict) -> dict:
    """Save a booking to Supabase and send a best-effort confirmation message.
    Shared by BOTH callers: the /book HTTP endpoint (Retell) and the VAPI voice
    flow (called from /chat/completions when the LangGraph run completes).
    Returns {ok, status, booking_id, confirmation_code, sms, message}.
    """
    row = {
        "caller_name": fields.get("caller_name") or fields.get("name"),
        "address": fields.get("address"),
        "problem": fields.get("problem"),
        "is_emergency": _as_bool(fields.get("is_emergency")),
        "time_preference": fields.get("time_preference") or fields.get("time"),
        "source": fields.get("source") or "retell",
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

    # Real confirmation message (best-effort — never blocks/fails the booking).
    # Recipient: the caller's phone if the flow collected one, else a fixed demo
    # number (SMS_TO_FALLBACK). On a Twilio trial this must be a verified/joined
    # number (or a WhatsApp-sandbox participant).
    sms = {"sent": False, "reason": "booking not saved"}
    if ok:
        to = fields.get("phone") or fields.get("to") or os.getenv("SMS_TO_FALLBACK")
        urgent = " (flagged URGENT)" if row["is_emergency"] else ""
        body = (
            f"AllSeasons HVAC: you're booked{urgent}. "
            f"{row['problem'] or 'your HVAC issue'} at "
            f"{row['address'] or 'your address'}, "
            f"{row['time_preference'] or 'the scheduled time'}. "
            f"Confirmation code {confirmation_code}."
        )
        sms = await _send_sms(to, body)

    return {
        "ok": ok,
        "status": r.status_code,
        "booking_id": booking_id,
        "confirmation_code": confirmation_code,
        "sms": sms,
        "message": (f"Booking saved. Confirmation code {confirmation_code}."
                    if ok else "Booking failed to save."),
    }


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

    # Retell wraps the function parameters inside "args" and puts the function
    # name at the top level. VAPI / curl send them flat. Accept either shape:
    # start from top-level, then let "args" override so Retell calls work too.
    fields = dict(data)
    if isinstance(data.get("args"), dict):
        fields = {**data, **data["args"]}

    return await save_booking(fields)


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

    # When the LangGraph flow reaches "done" (caller confirmed), book for REAL —
    # same Supabase insert + WhatsApp/SMS as the /book endpoint. Guard so a call
    # books only once, even though the model may ping us again after completion.
    if state.get("done") and session_id not in _booked_sessions:
        _booked_sessions.add(session_id)
        await save_booking({
            "problem": state.get("problem"),
            "address": state.get("address"),
            "is_emergency": state.get("is_emergency"),
            "time_preference": state.get("time_preference"),
            "source": "vapi",
        })

    return _sse_openai(state["reply"])
