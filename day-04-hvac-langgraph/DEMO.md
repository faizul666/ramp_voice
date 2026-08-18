# HVAC Agent — Demo Runbook

Step-by-step to run (or record) the AllSeasons HVAC demo. Follow top to bottom.
The "wow" is: **client watches the dashboard → you call → a booking appears live.**

---

## 0. Pre-flight (5 minutes before)

- [ ] **VAPI number points to HVAC.** VAPI → Phone Numbers → your number → Inbound → Assistant = **AllSeasons HVAC** (not Mia). Save.
- [ ] **Backend is up.** Open <https://hvac.bizlyt.com/health> → should show `{"ok":true}`.
      Do NOT redeploy right before/during a demo (a restart = a few seconds of downtime = a dropped call).
- [ ] **Dashboard is clean.** Open <https://hvac.bizlyt.com/dashboard>. Delete junk test rows in Supabase first; leave 1–2 tidy ones so it's not empty.
- [ ] **WhatsApp budget.** Trial = 5 messages/day. If you want the text to land live, make sure you haven't used today's 5 (or top up Twilio). If capped, that's fine — see "If WhatsApp is capped" below.
- [ ] **Phone ready.** The phone you'll call from. (US number → international call from BD; a "trial account" notice plays first on Twilio trial — ignore it.)

---

## 1. Set up the screen

Two things visible:
1. **Browser** on the **/dashboard** page (the green ● LIVE badge showing).
2. Your **phone** (on camera, or use a softphone so the call audio is on screen for a recording).

If recording (Loom): start recording now, on the dashboard.

---

## 2. Say the intro (10 seconds)

> "This is an after-hours AI receptionist for an HVAC company. When a customer calls
> after closing, it answers, figures out if it's an emergency, takes the booking, and
> logs it instantly. Watch this dashboard — it's live."

---

## 3. Make the call

Dial the number. Talk through a booking **out loud** so the audience hears both sides.
Use an **emergency** so they see the urgency flag:

| You say | The agent does |
|---|---|
| *(it greets)* | "Thanks for calling AllSeasons HVAC…" |
| **"My furnace is completely dead, no heat and it's freezing."** | Flags it **URGENT**, asks your name |
| **"Aminul."** | Asks the service address |
| **"12 Pine Street."** | Asks preferred time |
| **"Tomorrow at 9 in the morning."** | Reads the whole thing back to confirm |
| **"Yes, book it."** | "Perfect, you're all set…" → **books for real** |

---

## 4. Point at the dashboard (the payoff)

Within ~5 seconds, a **new row appears** at the top:
- **red URGENT badge**, name **Aminul**, "furnace dead", 12 Pine Street, tomorrow 9am,
  a **confirmation code**, and source **VAPI**.

Say:

> "That booking is now in their system, with an urgency flag, a confirmation code, and
> a full transcript — no human touched it. If it were routine, it'd be tagged routine
> instead and scheduled normally."

---

## 5. (If WhatsApp budget available) show the text

Hold up your phone — the **WhatsApp confirmation** arrives with the booking details and
the same confirmation code.

> "The customer also gets an instant confirmation on WhatsApp."

**If WhatsApp is capped today:** skip it. The confirmation code the agent *spoke* + the
live dashboard row are already proof. Mention: *"confirmations also go out by WhatsApp/SMS
— on the live account that's automatic per booking."*

---

## 6. Close with the value (talking points)

- **Never miss an after-hours call** = captured jobs instead of voicemail.
- **Emergency triage** = urgent jobs flagged and prioritized automatically.
- **Books straight into their system** — same backend works behind VAPI *or* Retell.
- **Keeps their existing number**: they just forward their line to the agent after hours.
- **Cost**: a setup fee + monthly, plus usage (per-minute + number) passed through.

---

## Troubleshooting (quick)

| Symptom | Fix |
|---|---|
| Agent greets but doesn't answer | Backend was mid-redeploy. Check `/health`, wait, retry. Never redeploy near a demo. |
| No row on dashboard | Refresh (it auto-refreshes every 5s). Check Supabase env vars are set in Coolify. |
| WhatsApp didn't arrive | Trial 5/day cap (error 63038) — wait for reset or top up Twilio. Booking still saved. |
| "Trial account" voice before call | Twilio trial notice — upgrade Twilio to remove it. |
| Wrong assistant answers | VAPI number's Inbound Assistant is still on Mia — switch it to HVAC. |

---

## Reset after the demo

- Switch the VAPI number back to **Mia** if you need the restaurant demo.
- Delete the demo row(s) from Supabase if you want a clean board next time.
