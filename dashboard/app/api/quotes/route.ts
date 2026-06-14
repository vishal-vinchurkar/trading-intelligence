// Live-quote proxy — server-side only, so the Alpaca keys never reach the browser.
// The dashboard fetches /api/quotes?symbols=AAPL,MSFT and renders the live price
// next to the EOD close. Signals stay computed on end-of-day data; this is display
// only. Requires ALPACA_API_KEY / ALPACA_SECRET_KEY in the server env (Vercel env
// vars or dashboard/.env.local) — NOT the NEXT_PUBLIC_ prefix (must stay private).

import { NextRequest, NextResponse } from "next/server";

const DATA_BASE = "https://data.alpaca.markets";
export const dynamic = "force-dynamic"; // never cache live prices

export async function GET(req: NextRequest) {
  const key = process.env.ALPACA_API_KEY;
  const sec = process.env.ALPACA_SECRET_KEY;
  if (!key || !sec) {
    return NextResponse.json(
      { error: "Alpaca keys not configured on the server", quotes: {} },
      { status: 200 }
    );
  }

  const raw = req.nextUrl.searchParams.get("symbols") ?? "";
  // Alpaca is US equities only — drop Indian (.NS) / index (^) symbols.
  const symbols = raw
    .split(",")
    .map((s) => s.trim().toUpperCase())
    .filter((s) => s && !s.includes(".") && !s.includes("^"))
    .slice(0, 100);
  if (symbols.length === 0) {
    return NextResponse.json({ quotes: {} });
  }

  const url = `${DATA_BASE}/v2/stocks/snapshots?symbols=${encodeURIComponent(
    symbols.join(",")
  )}&feed=iex`;

  try {
    const res = await fetch(url, {
      headers: { "APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec },
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json(
        { error: `Alpaca ${res.status}`, quotes: {} },
        { status: 200 }
      );
    }
    const snaps = (await res.json()) as Record<
      string,
      { latestTrade?: { p?: number; t?: string } }
    >;
    const quotes: Record<string, { price: number; time: string | null }> = {};
    for (const [sym, snap] of Object.entries(snaps)) {
      const p = snap?.latestTrade?.p;
      if (typeof p === "number") {
        quotes[sym] = { price: p, time: snap.latestTrade?.t ?? null };
      }
    }
    return NextResponse.json({ quotes });
  } catch (e) {
    return NextResponse.json(
      { error: String(e), quotes: {} },
      { status: 200 }
    );
  }
}
