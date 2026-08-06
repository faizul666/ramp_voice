"""
HVAC after-hours receptionist — LangGraph state machine (v2, LLM-powered).

The structure (state, nodes, edges) is identical to v1. What changed: the two
brittle spots — urgency and confirmation intent — now use Gemini to understand
MEANING instead of matching keywords. Falls back to keywords if no API key,
so it still runs offline.

Setup:  put GOOGLE_API_KEY=... in a .env file (see .env.example)
Try it: python graph.py
"""

import json
import os
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

load_dotenv()


# ---------- LLM helpers (Gemini) ----------

_llm = None


def _get_llm():
    """Provider-agnostic: DeepSeek if its key is set, else Gemini. Nodes don't care."""
    global _llm
    if _llm is None:
        if os.getenv("DEEPSEEK_API_KEY"):
            from langchain_openai import ChatOpenAI  # DeepSeek is OpenAI-compatible
            _llm = ChatOpenAI(
                model="deepseek-chat", temperature=0,
                base_url="https://api.deepseek.com",
                api_key=os.getenv("DEEPSEEK_API_KEY"),
            )
        elif os.getenv("GOOGLE_API_KEY"):
            from langchain_google_genai import ChatGoogleGenerativeAI
            _llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    return _llm


def _has_key() -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY") or os.getenv("GOOGLE_API_KEY"))


EMERGENCY_SIGNS = [  # fallback only, when no API key is set
    "no heat", "no cooling", "no ac", "gas", "smell", "leak", "sparks",
    "burning", "carbon monoxide", "freezing", "flood", "emergency",
]


def _kw_urgency(problem: str) -> bool:
    return any(sign in problem.lower() for sign in EMERGENCY_SIGNS)


def _kw_intent(text: str) -> str:
    t = text.lower()
    if "address" in t:
        return "change_address"
    if any(w in t for w in ["change", "different", "instead", "actually"]):
        return "change_time"
    if any(w in t for w in ["yes", "yeah", "yep", "ok", "sure", "correct", "book", "go ahead"]):
        return "confirm"
    if t.strip() in ("no", "nope"):
        return "decline"
    return "unclear"


def classify_urgency(problem: str) -> bool:
    """True if this HVAC problem is an emergency. Falls back to keywords if the LLM
    is unavailable (no key, or a transient network failure) so a call never crashes."""
    if not _has_key():
        return _kw_urgency(problem)
    prompt = (
        "You triage HVAC after-hours calls. Is the caller's problem an EMERGENCY "
        "(safety risk, no heat in cold weather, no cooling in dangerous heat, gas, "
        "smoke, sparks, leaks, or vulnerable people at risk)? "
        "Answer with only 'yes' or 'no'.\n\n"
        f"Problem: {problem}"
    )
    try:
        return _get_llm().invoke(prompt).content.strip().lower().startswith("y")
    except Exception:
        return _kw_urgency(problem)


def _extract_json(s: str) -> dict:
    i, j = s.find("{"), s.rfind("}")
    if i == -1 or j == -1:
        raise ValueError("no json object in response")
    return json.loads(s[i:j + 1])


def _kw_action(text: str) -> dict:
    label = _kw_intent(text)
    action = {"confirm": "confirm", "decline": "decline",
              "change_time": "change", "change_address": "change"}.get(label, "unclear")
    return {"action": action, "time": None, "address": None}


def interpret_confirmation(text: str, state: HVACState) -> dict:
    """Understand the caller's reply to the confirmation read-back AND pull out any
    inline correction in one turn. Returns:
      {action: confirm|change|decline|unclear, time: str|None, address: str|None}
    """
    if not _has_key():
        return _kw_action(text)
    prompt = (
        "A receptionist read back an HVAC booking and asked the caller to confirm.\n"
        f"Current booking — problem: {state.get('problem')!r}, "
        f"address: {state.get('address')!r}, time: {state.get('time_preference')!r}.\n"
        f"Caller replied: {text!r}\n\n"
        "Return ONLY a JSON object:\n"
        '  "action": "confirm" | "change" | "decline" | "unclear"\n'
        '  "time": the new preferred time if the caller stated one, else null\n'
        '  "address": the new address if the caller stated one, else null\n'
        'If the caller stated a new time or address, action must be "change".\n'
        'Example: {"action": "change", "time": "tomorrow at 8pm", "address": null}'
    )
    try:
        data = _extract_json(_get_llm().invoke(prompt).content)
        if data.get("action") not in {"confirm", "change", "decline", "unclear"}:
            data["action"] = "unclear"
        return data
    except Exception:
        return _kw_action(text)


# ---------- 1) STATE ----------

class HVACState(TypedDict, total=False):
    step: str
    user_input: str
    reply: str
    problem: str
    is_emergency: bool
    address: str
    time_preference: str
    done: bool
    _route: str


def summary(state: HVACState) -> str:
    tag = "URGENT — " if state.get("is_emergency") else ""
    return (f"{tag}{state.get('problem', '(problem)')} at "
            f"{state.get('address', '(address)')}, "
            f"preferred time {state.get('time_preference', '(time)')}")


# ---------- 2) NODES ----------

def greet(state: HVACState) -> HVACState:
    return {
        "reply": "Thanks for calling AllSeasons HVAC, after-hours line. "
                 "What's going on with your heating or cooling?",
        "step": "identify_problem",
    }


def identify_problem(state: HVACState) -> HVACState:
    problem = state.get("user_input", "").strip()
    emergency = classify_urgency(problem)   # <-- LLM judges meaning, not keywords
    ack = ("That sounds urgent — I'm flagging this as an emergency and we'll "
           "prioritize you. " if emergency else "Got it, thank you. ")
    return {
        "problem": problem,
        "is_emergency": emergency,
        "reply": ack + "What's the service address?",
        "step": "collect_address",
    }


def collect_address(state: HVACState) -> HVACState:
    return {
        "address": state.get("user_input", "").strip(),
        "reply": "Thanks. What day and time works best for the visit?",
        "step": "time_preference",
    }


def time_preference(state: HVACState) -> HVACState:
    tp = state.get("user_input", "").strip()
    merged = {**state, "time_preference": tp}
    return {
        "time_preference": tp,
        "reply": f"Let me confirm: {summary(merged)}. Should I book that?",
        "step": "confirm",
    }


def confirm(state: HVACState) -> HVACState:
    r = interpret_confirmation(state.get("user_input", ""), state)  # understand + extract
    action = r.get("action")

    if action == "confirm":
        return {"_route": "send_sms"}

    if action == "change":
        # Apply any inline correction (e.g. "make it 8pm") and re-confirm in one turn.
        updates: HVACState = {}
        if r.get("time"):
            updates["time_preference"] = r["time"]
        if r.get("address"):
            updates["address"] = r["address"]
        if updates:
            merged = {**state, **updates}
            return {**updates,
                    "reply": f"Got it. Let me re-confirm: {summary(merged)}. Should I book that?",
                    "step": "confirm", "_route": "wait"}
        return {"reply": "Sure — what would you like to change, the time or the address?",
                "step": "confirm", "_route": "wait"}

    if action == "decline":
        return {"reply": "No problem — what would you like to change?",
                "step": "confirm", "_route": "wait"}

    return {"reply": "Sorry — should I book it as is, or change something?",
            "step": "confirm", "_route": "wait"}


def send_sms(state: HVACState) -> HVACState:
    time = state.get("time_preference", "the scheduled time")
    if state.get("is_emergency"):
        # Problem is urgent, but honor the time they chose — no contradictory promise.
        closer = (f"I've flagged this as urgent and we've got you down for {time}. "
                  "If it gets worse before then, call us right back and we'll dispatch "
                  "a technician immediately.")
    else:
        closer = f"A technician will see you {time}."
    return {
        "reply": f"Perfect, you're all set. I've texted a confirmation. {closer} "
                 "Thanks for calling!",
        "done": True,
        "step": "done",
    }


# ---------- 3) EDGES ----------

def entry(state: HVACState) -> str:
    return state.get("step", "greet")


def after_confirm(state: HVACState) -> str:
    return state.get("_route", "wait")


builder = StateGraph(HVACState)
for name, fn in [
    ("greet", greet), ("identify_problem", identify_problem),
    ("collect_address", collect_address), ("time_preference", time_preference),
    ("confirm", confirm), ("send_sms", send_sms),
]:
    builder.add_node(name, fn)

builder.add_conditional_edges(START, entry, {
    "greet": "greet", "identify_problem": "identify_problem",
    "collect_address": "collect_address", "time_preference": "time_preference",
    "confirm": "confirm", "send_sms": "send_sms", "done": END,
})
for name in ["greet", "identify_problem", "collect_address", "time_preference", "send_sms"]:
    builder.add_edge(name, END)
builder.add_conditional_edges("confirm", after_confirm, {"send_sms": "send_sms", "wait": END})

graph = builder.compile()


if __name__ == "__main__":
    mode = ("DeepSeek" if os.getenv("DEEPSEEK_API_KEY")
            else "Gemini" if os.getenv("GOOGLE_API_KEY")
            else "keyword fallback (no LLM key)")
    print(f"[LLM mode: {mode}]")
    state: HVACState = {"step": "greet", "user_input": ""}
    state = graph.invoke(state)
    print("BOT:", state["reply"])
    while not state.get("done"):
        try:
            state["user_input"] = input("YOU: ")
        except (EOFError, KeyboardInterrupt):
            print("\n[ended]")
            break
        state = graph.invoke(state)
        print("BOT:", state["reply"])
