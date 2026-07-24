# Day 1 Demo — Bella Nova reservation bot (Mia)

**Live proof:** Mia answered a real phone call (VAPI-provisioned number) and booked a table.

## Recording
- 60-second demo link: <paste Loom / screen-recording / VAPI call-recording link here>
- Source: (VAPI auto-recording  |  phone screen-record  |  Loom)

## Call facts
- Stack: VAPI (orchestration) + Google Gemini Flash (LLM) + Deepgram (STT) + ElevenLabs/VAPI voice (TTS)
- Number: VAPI-provisioned (Path A)
- Avg turn latency: ~2655ms (baseline to beat on Day 2)

## What it demonstrates
- One-question-at-a-time booking flow
- Handles "closed Mondays" + human-handoff edge cases
- Live on the real phone network
