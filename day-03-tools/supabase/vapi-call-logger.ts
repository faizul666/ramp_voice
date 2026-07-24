// Supabase Edge Function: vapi-call-logger
// Receives VAPI's end-of-call-report webhook and writes one row to call_logs.
// Deploy in Supabase dashboard -> Edge Functions. IMPORTANT: turn OFF "Verify JWT".
// SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are injected automatically.

import { createClient } from "jsr:@supabase/supabase-js@2";

Deno.serve(async (req) => {
  try {
    const body = await req.json();
    const msg = body?.message ?? {};

    if (msg.type !== "end-of-call-report") {
      return new Response("ignored", { status: 200 });
    }

    const call = msg.call ?? {};
    const analysis = msg.analysis ?? {};

    // DEBUG: log the raw payload so we can see the real shape in Edge Function logs.
    console.log("VAPI payload:", JSON.stringify(body).slice(0, 4000));

    // The newer "Structured Outputs" may land under different keys than the older
    // structuredData. Check every likely location.
    const rawSd = analysis.structuredData
      ?? analysis.structuredOutputs
      ?? msg.structuredData
      ?? msg.structuredOutputs
      ?? {};
    const sd: Record<string, unknown> = {};
    for (const v of Object.values(rawSd)) {
      if (v && typeof v === "object" && "name" in (v as Record<string, unknown>)) {
        const item = v as { name: string; result: unknown };
        sd[item.name] = item.result;
      }
    }
    for (const [k, v] of Object.entries(rawSd)) {
      if (!(v && typeof v === "object" && "name" in (v as Record<string, unknown>))) {
        sd[k] = v;
      }
    }

    const partyNum = Number(sd.party_size);

    const row = {
      // `reservation` fallback covers the earlier output named "reservation".
      caller_name: (sd.caller_name ?? sd.reservation ?? null) as string | null,
      caller_phone: (sd.caller_phone ?? call?.customer?.number ?? null) as string | null,
      party_size: Number.isFinite(partyNum) ? partyNum : null,
      reservation_time: (sd.reservation_time ?? null) as string | null,
      outcome: (sd.outcome ?? msg.endedReason ?? null) as string | null,
      summary: msg.summary ?? analysis.summary ?? null,
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
