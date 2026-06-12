import { Disclaimer } from "@/components/Disclaimer";
import { TickerSearch } from "@/components/TickerSearch";
import { fetchLatestSignals, isSupabaseConfigured } from "@/lib/supabase";

// Server component: fetch the latest signal per ticker at request time, then
// hand the set to the client TickerSearch for filtering.
export const dynamic = "force-dynamic";

export default async function Home() {
  const signals = isSupabaseConfigured ? await fetchLatestSignals() : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Latest signals</h1>
          <p className="mt-1 text-sm text-muted">
            One card per tracked ticker — newest arbitrated verdict, the two
            upstream agent signals, and the 5/15/30-day call.
          </p>
        </div>
        <Disclaimer />
      </div>

      {!isSupabaseConfigured ? (
        <EmptyState
          title="Supabase not configured"
          body="Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in the environment, then reload."
        />
      ) : signals.length === 0 ? (
        <EmptyState
          title="No signals yet"
          body="Run the pipeline to populate predictions: PYTHONPATH=. python -m orchestrator.orchestrator AAPL"
        />
      ) : (
        <TickerSearch signals={signals} />
      )}
    </div>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-panel/40 px-6 py-16 text-center">
      <div className="text-base font-medium">{title}</div>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted">{body}</p>
    </div>
  );
}
