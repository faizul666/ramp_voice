# Day 1 — VAPI dashboard fluency + latency fundamentals

**Goal:** build your first voice agent in the VAPI dashboard and understand the
STT → LLM → TTS pipeline. Ship a callable restaurant reservation bot + a 60s demo recording.

**Time:** ~2 hrs build + 1 hr proposals (the non-negotiable parallel rule).

---

## Part A — Accounts (30 min, you do this by hand)
1. **VAPI** — https://vapi.ai → sign up (Google login is fine).
2. **ElevenLabs** — https://elevenlabs.io → free tier. Grab your API key later if VAPI asks.
3. **Twilio** — https://twilio.com → $15 trial credit. You'll buy a phone number ($1/mo) in Part D.

> You don't strictly need ElevenLabs/Twilio keys to *test in the browser*. VAPI has a
> built-in web tester. You need Twilio only to attach a real phone number.

## Part B — The pipeline (understand before you build, 10 min)
Every voice turn is 3 hops:
- **STT** (speech-to-text): your words → text. VAPI default: Deepgram.
- **LLM** (the brain): text → a text reply. Pick GPT-4o-mini or similar to start (fast + cheap).
- **TTS** (text-to-speech): reply text → audio. ElevenLabs or VAPI's default voice.

**Latency = sum of all three hops + network.** Target: under ~800ms "response latency."
Levers that cut it: a fast/small LLM, streaming TTS, a short system prompt, low `maxTokens`.

## Part C — Build the assistant in the VAPI dashboard (40 min)
1. VAPI dashboard → **Assistants** → **Create Assistant** (blank template).
2. **Model**: OpenAI `gpt-4o-mini` (fast). Paste the system prompt from `system-prompt.md`.
3. **Voice**: pick any ElevenLabs voice (e.g. "Rachel") or VAPI default.
4. **Transcriber**: Deepgram (default) — leave it.
5. **First message**: set it to the greeting (see system-prompt.md).
6. Click **Talk to Assistant** (browser mic) and run the test conversation.

Tune for latency/feel:
- Keep `maxTokens` low (~150). Long replies = long TTS = dead air.
- Model temperature ~0.5.
- Note the response-latency number VAPI shows after the call.

## Part D — Attach a Twilio number (20 min)
1. Twilio console → buy a number (voice-capable, ~$1).
2. VAPI dashboard → **Phone Numbers** → **Import** your Twilio number (needs Twilio SID + Auth Token).
3. Assign the number to your restaurant assistant.
4. **Call it from your phone.** It should greet you and take a reservation.

## Part E — Ship (20 min)
- Record a **60-second demo** of you calling the bot (phone screen-record or Loom).
- Save it to `recordings/` (gitignored) or drop the Loom link in `DEMO.md`.
- Fill in `NOTES.md` with the response-latency number and how it felt.

## Reading (parallel / while things load)
- keesvandenbos/voice-agent-builder → the "latency, not raw quality, kills voice agents" section.

## Done-when checklist
- [ ] VAPI + ElevenLabs + Twilio accounts created
- [ ] Restaurant assistant built, tested in browser
- [ ] Twilio number attached, called it from a real phone
- [ ] 60s demo recorded, link in DEMO.md
- [ ] NOTES.md has the latency number + one thing you'd improve
- [ ] **(parallel)** sent/queued your first Upwork proposal
