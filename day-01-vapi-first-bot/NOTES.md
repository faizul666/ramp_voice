# Day 1 — Notes

## Latency observed
- Response latency (from VAPI call summary): 2655 ms avg over 8 turns (Gemini Flash via Google provider)
- Felt: "alright — not fast, not laggy" (felt OK, but meter says ~3x over the 800ms target)
- Lesson: trust the meter over the vibe. Baseline to BEAT on Day 2.

## What worked
- Mia greets correctly, asks one question at a time
- Handled both hard cases: "closed Mondays" rule + human handoff (took name/number gracefully)

## What I'd improve (feeds Day 2 prompt rewrite)
- Cut the ~2655ms turn latency: shorten the system prompt (60-70% shorter), lower maxTokens further
- Consider whether Google/Gemini first-token latency is a factor vs the prompt length

## Demo
- 60s recording link: (see DEMO.md)

## Proposals (parallel rule)
- Sent today: ___
- Replies so far: ___
