import { NextResponse } from "next/server";
import { fetchLatestSignals, isSupabaseConfigured } from "@/lib/supabase";

// Read endpoint: latest signal per tracked ticker. Server-rendered pages call
// the lib helpers directly; this route exists for external polling / the cron
// worker (Phase 4) and for client-side refreshes.
export const dynamic = "force-dynamic";

export async function GET() {
  if (!isSupabaseConfigured) {
    return NextResponse.json(
      { configured: false, signals: [] },
      { status: 200 }
    );
  }
  try {
    const signals = await fetchLatestSignals();
    return NextResponse.json({ configured: true, signals });
  } catch (err) {
    return NextResponse.json(
      { configured: true, error: (err as Error).message, signals: [] },
      { status: 500 }
    );
  }
}
