# Day 2 — Mia prompt v2 (voice-tuned, ~60% shorter)

Same bot as Day 1, rewritten for voice: compressed style, protected facts,
sixth-grade English, one question at a time.

## First message (greeting) — unchanged
> Thanks for calling Bella Nova. This is Mia — are you looking to make a reservation?

## System prompt v2 (paste into VAPI → Model → System Prompt, replacing v1)

```
You are Mia, the phone host for Bella Nova, an Italian restaurant.
Your only job: book, change, or cancel a table.

How to talk: warm and quick, like a real host. Short sentences. Ask ONE thing,
then stop and listen. Keep replies under two sentences. Say numbers naturally
("seven thirty PM", "a table for four"). Never read lists, emails, or web links.

To book, collect these one at a time: date and time, party size, name, phone
number. Read the phone number back. Then repeat the whole booking once and ask
"Should I lock that in?"

Hours: open Tuesday to Sunday, 5 PM to 10 PM. Closed Mondays. Last seating 9:30 PM.
If they ask for Monday, before 5 PM, or after 9:30 PM: say you're closed then and
offer the nearest open time.

If you can't help (private events, catering, allergies) or they ask for a human:
say someone will call them right back, take their name and number, end warmly.
If they go quiet: ask "Would you like me to suggest a time?"
End finished calls with a short confirmation and "See you then!"
```

## What changed from v1 (and why)
- Killed all the markdown headers and the numbered "what you must collect" list —
  folded into one sentence. Model doesn't need pretty formatting; it costs tokens.
- Merged the 5 separate "Rules" bullets into 3 plain-English lines.
- KEPT every fact intact: hours, closed Mondays, last seating 9:30. Facts protect
  against hallucination.
- Result: ~60% fewer tokens re-read on every turn → lower latency.

## Measure again (the point of today)
- Day 1 baseline: ~2655ms avg / turn
- v2 result: **1625ms** avg / turn  → cut ~1030ms (~39%) purely by shortening the prompt
- After wiring own ElevenLabs key + picking a FAST model (Flash/Turbo v2.5): **1310ms**
- Full arc: 2655 → 1625 (prompt) → 1310 (fast ElevenLabs voice). ~50% cut over Day 1-2.
- Takeaway: when a voice bot feels slow, audit the prompt BEFORE swapping models/infra;
  and a premium voice provider can still be fast IF you pick its real-time model, not its
  audiobook model (Multilingual v2 = slow; Flash/Turbo v2.5 = fast).

## Gotcha found on Day 2: Gemini free-tier 429s under load
- Interrupting (barge-in) fires an extra LLM request instantly, on top of the in-flight one.
- Gemini FREE tier has a low requests-per-minute cap → two rapid calls = `pipeline-error-google-429-exceeded-quota` → call DROPS.
- This is THE reason you never ship a production voice agent on a free LLM key. Busy calls
  (interruptions, tool-calling, multi-step) all burst requests and will hit the cap.
- Fixes: (a) test gently on free tier (one interruption per call, pause between calls), or
  (b) durable fix = add billing to the Gemini API key — Flash is ~fractions of a cent/call, or
  (c) use a VAPI-fronted model on trial credits. For CLIENT demos: never free tier.
```
