// Supabase Edge Function: vapi-call-logger
// Receives VAPI's end-of-call-report webhook and writes one row to call_logs.
// Deploy in Supabase dashboard -> Edge Functions. IMPORTANT: turn OFF "Verify JWT".
// SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are injected automatically.
//
// NOTE: VAPI computes `analysis` (summary + structured outputs) asynchronously, so it's
// EMPTY in this webhook even on completed calls. So we read the booking directly from the
// book_reservation tool call inside artifact.messages instead.

import { createClient } from "jsr:@supabase/supabase-js@2";

// Find the book_reservation tool call in the transcript and return its arguments.
function findBookingArgs(messages: unknown): Record<string, unknown> | null {
  if (!Array.isArray(messages)) return null;
  for (const m of messages as Record<string, unknown>[]) {
    const toolCalls = (m.toolCalls ?? m.tool_calls) as unknown;
    if (!Array.isArray(toolCalls)) continue;
    for (const tc of toolCalls as Record<string, unknown>[]) {
      const fn = (tc.function ?? tc) as Record<string, unknown>;
      if (fn?.name === "book_reservation") {
        let args: unknown = fn.arguments;
        if (typeof args === "string") {
          try { args = JSON.parse(args); } catch { args = {}; }
        }
        return (args ?? {}) as Record<string, unknown>;
      }
    }
  }
  return null;
}

Deno.serve(async (req) => {
  try {
    const body = await req.json();
    const msg = body?.message ?? {};

    if (msg.type !== "end-of-call-report") {
      return new Response("ignored", { status: 200 });
    }

    const call = msg.call ?? {};
    const analysis = msg.analysis ?? {};
    const messages = msg.artifact?.messages;

    // DEBUG: see what roles are in the transcript (helps if the tool call isn't found).
    if (Array.isArray(messages)) {
      console.log("roles:", JSON.stringify(messages.map((m: Record<string, unknown>) => m.role)));
    }

    // Primary source: the booking tool call in the transcript.
    const b = findBookingArgs(messages) ?? {};
    console.log("booking args:", JSON.stringify(b));

    // Fallback: VAPI structured outputs (UUID-keyed) IF analysis happens to be present.
    const rawSd = analysis.structuredData ?? analysis.structuredOutputs ?? {};
    const sd: Record<string, unknown> = {};
    for (const v of Object.values(rawSd)) {
      if (v && typeof v === "object" && "name" in (v as Record<string, unknown>)) {
        const item = v as { name: string; result: unknown };
        sd[item.name] = item.result;
      }
    }

    const partyRaw = b.partySize ?? sd.party_size;
    const partyNum = Number(partyRaw);
    const booked = Object.keys(b).length > 0;

    let callerName = (b.name ?? sd.caller_name ?? sd.reservation ?? null) as string | null;
    let callerPhone = (b.phone ?? sd.caller_phone ?? call?.customer?.number ?? null) as string | null;
    const partySize = Number.isFinite(partyNum) ? partyNum : null;
    const reservationTime = (b.startDateTime ?? sd.reservation_time ?? null) as string | null;

    // Layer 2 validation: correct the classic name/phone field swap.
    // A "name" that is mostly digits and has no real word is actually a phone.
    const looksLikePhone = (s: string | null) =>
      typeof s === "string" && (s.match(/\d/g)?.length ?? 0) >= 6 && !/[a-zA-Z]{2,}/.test(s);
    if (looksLikePhone(callerName) && callerPhone && !looksLikePhone(callerPhone)) {
      [callerName, callerPhone] = [callerPhone, callerName]; // swap back
    }
    // Normalize phone to digits (and a leading +) only.
    if (typeof callerPhone === "string") {
      callerPhone = callerPhone.replace(/[^\d+]/g, "") || null;
    }
    // Reject junk names: the model sometimes writes a field label as the value
    // (e.g. the literal word "phone"). Store null instead of a wrong value.
    const junkNames = new Set([
      "phone", "name", "number", "phone number", "none", "null", "n/a", "na", "unknown",
    ]);
    if (typeof callerName === "string" && junkNames.has(callerName.trim().toLowerCase())) {
      callerName = null;
    }

    // Build a readable summary from what we have (VAPI's analysis.summary is empty at
    // webhook time). Fall back to VAPI's summary if it ever arrives populated.
    const derivedSummary = booked
      ? `Booked a table for ${partySize ?? "?"} on ${reservationTime ?? "?"} under ${callerName ?? "guest"}.`
      : `Call ended (${msg.endedReason ?? "unknown"}) with no booking.`;

    const row = {
      caller_name: callerName,
      caller_phone: callerPhone,
      party_size: partySize,
      reservation_time: reservationTime,
      outcome: (sd.outcome ?? (booked ? "booked" : (msg.endedReason ?? null))) as string | null,
      summary: msg.summary || analysis.summary || derivedSummary,
      transcript: msg.transcript ?? msg.artifact?.transcript ?? null,
      call_id: call?.id ?? null,
    };

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    );

    const { error } = await supabase.from("call_logs").insert(row);
    if (error) {
      console.error("insert error:", error);
      return new Response(JSON.stringify(error), { status: 500 });
    }

    return new Response("logged", { status: 200 });
  } catch (e) {
    console.error("handler error:", e);
    return new Response("error", { status: 200 });
  }
});
