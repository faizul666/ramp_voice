# VAPI vs Retell — when to pick which (my working one-pager)

> My decision cheat-sheet for proposals. Filled in from hands-on experience,
> not marketing pages. Update as I learn more.

## TL;DR
- **Reach for VAPI when:** the logic is the product — custom validation, branching,
  fallbacks, integrations you own. You bring a backend (my LangGraph brain) and want
  full control over every turn.
- **Reach for Retell when:** you need a working, testable flow *fast*. The Conductor
  copilot generates the whole state machine from a paragraph, and testing/SMS are
  built in. Great for demos and straightforward booking/intake bots.

## Side-by-side (fill in from direct experience)

| Dimension | VAPI | Retell |
|---|---|---|
| Build model | Assistants + custom LLM (my LangGraph backend) | Conversation Flow (visual state machine), Single-Prompt, Custom LLM |
| Custom/orchestrated logic | Full — my own backend, any code | Good — visual nodes + custom-function calls to my API; complex logic lives behind the API, not in the flow |
| No-code speed | slower (I wire it) | very fast — Conductor built 8 nodes from a paragraph in ~1 min |
| Provider flexibility (STT/LLM/TTS) | high — swap freely | selectable, default GPT-4.1; less emphasis on free swapping |
| Built-in evaluation/testing tools | external (my own smoketest) | strong — Test + Simulation tabs are first-class |
| Latency (felt) | good once tuned (~1.3s after ElevenLabs) | snappy in test; comparable |
| Pricing model | per-minute + my own LLM/infra costs | per-minute, bundled |
| Phone number / telephony | Twilio import or VAPI number | built-in numbers + Twilio |
| Learning curve | steeper — you build the brain | gentle — Conductor + visual flow |

## What surprised me (notes as I build)
- Retell has an AI **"Conductor"** copilot that interviews you (asks about APIs, SMS, etc.)
  then generates the visual flow. VAPI has no equivalent — you wire it all yourself.
- **Flex Mode vs Rigid Mode** toggle = a determinism dial. Same rigid-vs-flexible tension
  I handled in LangGraph, but Retell exposes it as a setting.
- **Built-in SMS tool** — native. In VAPI/LangGraph I'd wire Twilio myself.
- Built-in **Test + Simulation** tabs — testing is first-class.
- Default LLM was GPT-4.1 (provider is selectable; need to check how flexible vs VAPI).
- **Conductor generated the ENTIRE flow from a paragraph** in ~1 min: 8 nodes
  (Greeting, Assess Problem, Contact & Address, Preferred Time, Readback & Confirm,
  Book Appointment function, End-Booked, End-Failed) — the same state machine I
  hand-coded in LangGraph on Day 4. It even auto-created success/failure end
  branches from my API contract's `ok` field. Days of code → minutes in a GUI.
- Trade-off: I gave up fine control. My LangGraph version has custom validation
  (name/phone swap-fix, junk guards), resilient LLM fallbacks, and inline-correction
  logic — things I'd have to check/rebuild inside Retell's nodes.

## The line I'll use in proposals
> I build on both VAPI and Retell and pick per project — Retell when you want a
> polished flow live quickly, VAPI when the call logic needs custom control. Either
> way the booking runs through one backend I own, so your data lands where you need
> it and the agent behaves the same no matter the platform.
