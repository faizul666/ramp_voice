"""
HVAC after-hours receptionist — LangGraph state machine (v2, LLM-powered).

The structure (state, nodes, edges) is identical to v1. What changed: the two
brittle spots — urgency and confirmation intent — now use Gemini to understand
MEANING instead of matching keywords. Falls back to keywords if no API key,
so it still runs offline.

Setup:  put GOOGLE_API_KEY=... in a .env file (see .env.example)
Try it: python graph.py
"""

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


def classify_urgency(problem: str) -> bool:
    """True if this HVAC problem is an emergency."""
    if not _has_key():
        return any(sign in problem.lower() for sign in EMERGENCY_SIGNS)
    prompt = (
        "You triage HVAC after-hours calls. Is the caller's problem an EMERGENCY "
        "(safety risk, no heat in cold weather, no cooling in dangerous heat, gas, "
        "smoke, sparks, leaks, or vulnerable people at risk)? "
        "Answer with only 'yes' or 'no'.\n\n"
        f"Problem: {problem}"
    )
    return _get_llm().invoke(prompt).content.strip().lower().startswith("y")


def classify_intent(text: str) -> str:
    """One of: confirm, change_time, change_address, decline, unclear."""
    if not _has_key():
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
    prompt = (
        "A receptionist just read back a booking and asked the caller to confirm. "
        "Classify the caller's reply as exactly one of these labels: "
        "confirm, change_time, change_address, decline, unclear. "
        "Reply with only the label.\n\n"
        f"Caller: {text}"
    )
    label = _get_llm().invoke(prompt).content.strip().lower()
    valid = {"confirm", "change_time", "change_address", "decline", "unclear"}
    return label if label in valid else "unclear"


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
    ack = ("That sounds urgent — I'm flagging this as an emergency, a "
           "technician will call within the hour. " if emergency
           else "Got it, thank you. ")
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
    intent = classify_intent(state.get("user_input", ""))   # <-- LLM reads intent
    if intent == "change_address":
        return {"reply": "No problem — what's the correct service address?",
                "step": "collect_address", "_route": "wait"}
    if intent in ("change_time", "decline"):
        return {"reply": "Sure — what day and time would you prefer instead?",
                "step": "time_preference", "_route": "wait"}
    if intent == "confirm":
        return {"_route": "send_sms"}
    return {"reply": "Sorry — should I book it as is, or change something?",
            "step": "confirm", "_route": "wait"}


def send_sms(state: HVACState) -> HVACState:
    closer = ("A technician will call you within the hour."
              if state.get("is_emergency") else "A technician will see you then.")
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
