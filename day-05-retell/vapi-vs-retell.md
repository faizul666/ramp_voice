# VAPI vs Retell — when to pick which (my working one-pager)

> My decision cheat-sheet for proposals. Filled in from hands-on experience,
> not marketing pages. Update as I learn more.

## TL;DR (fill in after building in both)
- **Reach for VAPI when:** _______
- **Reach for Retell when:** _______

## Side-by-side (fill in from direct experience)

| Dimension | VAPI | Retell |
|---|---|---|
| Build model | Assistants + custom LLM (my LangGraph backend) | Conversation Flow (visual state machine), Single-Prompt, Custom LLM |
| Custom/orchestrated logic | Full — my own backend, any code | ? (how far does the visual flow go?) |
| No-code speed | slower (I wire it) | ? (how fast to a working flow?) |
| Provider flexibility (STT/LLM/TTS) | high — swap freely | ? |
| Built-in evaluation/testing tools | ? | reportedly stronger — verify |
| Latency (felt) | ? | ? |
| Pricing model | ? | ? |
| Phone number / telephony | Twilio import or VAPI number | ? |
| Learning curve | steeper | ? |

## What surprised me (notes as I build)
- Retell has an AI **"Conductor"** copilot that interviews you (asks about APIs, SMS, etc.)
  then generates the visual flow. VAPI has no equivalent — you wire it all yourself.
- **Flex Mode vs Rigid Mode** toggle = a determinism dial. Same rigid-vs-flexible tension
  I handled in LangGraph, but Retell exposes it as a setting.
- **Built-in SMS tool** — native. In VAPI/LangGraph I'd wire Twilio myself.
- Built-in **Test + Simulation** tabs — testing is first-class.
- Default LLM was GPT-4.1 (provider is selectable; need to check how flexible vs VAPI).

## The line I'll use in proposals
> _______ (one or two sentences a client would find reassuring)
