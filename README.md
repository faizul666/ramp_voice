# Voice AI Agent Ramp — VAPI / Retell Portfolio

A 10-day ramp to ship 3 production-grade voice AI agents and launch an Upwork gig:
**"AI Voice Agent MVP in 7 Days — VAPI or Retell + Multi-Step Logic + CRM Integration."**

The pipeline every voice agent runs on:

```
  Caller speaks ──► [ STT ]  ──►  [ LLM ] ──►  [ TTS ] ──► Caller hears
                 speech→text   the "brain"   text→speech
                 (Deepgram)   (GPT/Claude)  (ElevenLabs)
```

**The #1 rule of this whole ramp: latency, not raw quality, kills voice agents.**
Every extra 200ms of dead air makes the bot feel broken. Callers forgive a slightly
robotic voice; they hang up on a bot that pauses too long before answering.

## Portfolio projects
| # | Project | Stack | Status |
|---|---------|-------|--------|
| 1 | Restaurant Reservation Voice Agent | VAPI + Twilio + Calendar + Supabase | 🔨 Day 1–3 |
| 2 | HVAC After-Hours Receptionist | VAPI + LangGraph + Supabase + dashboard | ⬜ Day 4–6 |
| 3 | Outbound Lead Reactivation Agent | Retell + Supabase + pgvector RAG | ⬜ Day 7–9 |

## The non-negotiable rule
**Bid in parallel.** 2 hrs/day building, 1 hr/day sending Upwork proposals — starting Day 1,
not Day 11. Building supports bidding, not the other way around.
Day-3 check-in: Project 1 demo link + first proposal reply count.

## Layout
- `day-01-vapi-first-bot/` — accounts, VAPI quickstart, first restaurant bot
- (folders added per day)

## Accounts needed (Day 1)
- [ ] VAPI — https://vapi.ai
- [ ] ElevenLabs (free tier) — https://elevenlabs.io
- [ ] Twilio ($15 trial) — https://twilio.com
