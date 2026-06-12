import Link from "next/link";
import { notFound } from "next/navigation";
import { AgentOutputPanel } from "@/components/AgentOutputPanel";
import { Disclaimer } from "@/components/Disclaimer";
import {
  alignmentChip,
  confidencePct,
  directionArrow,
  directionColor,
  formatWhen,
  signalChip,
  verdictStyles,
} from "@/lib/display";
import {
  fetchLatestAgentOutputs,
  fetchTickerHistory,
  isSupabaseConfigured,
} from "@/lib/supabase";

export const dynamic = "force-dynamic";

// Per-ticker detail: the latest verdict in full (prediction legs, invalidation,
// risk/reward, reasoning), the three raw agent outputs (the isolation story),
// and the prediction history below.
export default async function TickerPage({
  params,
}: {
  params: Promise<{ symbol: string }>;
}) {
  const { symbol: rawSymbol } = await params;
  const symbol = decodeURIComponent(rawSymbol);

  if (!isSupabaseConfigured) {
    return (
      <div className="space-y-4">
        <BackLink />
        <p className="text-sm text-muted">
          Supabase is not configured, so per-ticker data is unavailable.
        </p>
      </div>
    );
  }

  const { ticker, predictions } = await fetchTickerHistory(symbol);
  if (!ticker || predictions.length === 0) notFound();

  const latest = predictions[0];
  const agentOutputs = await fetchLatestAgentOutputs(ticker.id);
  const v = verdictStyles[latest.verdict] ?? verdictStyles.WATCH;

  const legs = [
    { label: "5 day", leg: latest.prediction_5d },
    { label: "15 day", leg: latest.prediction_15d },
    { label: "30 day", leg: latest.prediction_30d },
  ];

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <BackLink />
          <div className="mt-2 flex items-baseline gap-3">
            <h1 className="font-mono text-3xl font-bold tracking-tight">
              {ticker.symbol}
            </h1>
            <span className="text-sm text-muted">
              {ticker.name ? `${ticker.name} · ` : ""}
              {ticker.market}
              {ticker.exchange ? `/${ticker.exchange}` : ""}
            </span>
          </div>
        </div>
        <Disclaimer />
      </div>

      {/* Verdict block */}
      <section className={`rounded-xl border border-border bg-panel p-6 ring-1 ${v.ring}`}>
        <div className="flex flex-wrap items-center gap-3">
          <span className={`rounded-lg px-3 py-1.5 text-xl font-bold ${v.chip}`}>
            {latest.verdict}
          </span>
          <span className="text-sm text-muted">
            confidence{" "}
            <span className={`font-mono ${v.text}`}>
              {confidencePct(latest.confidence)}
            </span>
          </span>
          {latest.signal_alignment && (
            <span className={`rounded px-2 py-0.5 text-xs ${alignmentChip(latest.signal_alignment)}`}>
              {latest.signal_alignment}
            </span>
          )}
          <span className={`rounded px-2 py-0.5 text-xs ${signalChip(latest.technical_signal)}`}>
            T·{latest.technical_signal ?? "—"}
          </span>
          <span className={`rounded px-2 py-0.5 text-xs ${signalChip(latest.fundamental_signal)}`}>
            F·{latest.fundamental_signal ?? "—"}
          </span>
          <span className="ml-auto text-xs text-muted">{formatWhen(latest.created_at)}</span>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {legs.map(({ label, leg }) => (
            <div key={label} className="rounded-lg border border-border bg-bg/50 p-4">
              <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
              <div className={`mt-1 text-lg ${directionColor(leg?.direction)}`}>
                {directionArrow(leg?.direction)} {leg?.direction ?? "—"}
              </div>
              <div className="text-sm text-muted">{leg?.magnitude ?? "—"}</div>
            </div>
          ))}
        </div>

        {latest.reasoning && (
          <p className="mt-5 text-sm leading-relaxed text-white/90">{latest.reasoning}</p>
        )}

        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {latest.invalidation && (
            <Field label="Invalidation" value={latest.invalidation} />
          )}
          {latest.risk_reward && (
            <Field label="Risk / reward" value={latest.risk_reward} mono />
          )}
        </div>
      </section>

      {/* Raw agent outputs */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
          Agent reports — show the work
        </h2>
        {agentOutputs.length === 0 ? (
          <p className="text-sm text-muted">
            Raw agent outputs weren&apos;t persisted for this run.
          </p>
        ) : (
          <div className="space-y-3">
            {agentOutputs
              .sort((a, b) => order(a.agent) - order(b.agent))
              .map((o) => (
                <AgentOutputPanel key={o.id} output={o} />
              ))}
          </div>
        )}
      </section>

      {/* History */}
      {predictions.length > 1 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
            Prediction history
          </h2>
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-panel text-left text-xs text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">When</th>
                  <th className="px-4 py-2 font-medium">Verdict</th>
                  <th className="px-4 py-2 font-medium">Conf.</th>
                  <th className="px-4 py-2 font-medium">Alignment</th>
                  <th className="px-4 py-2 font-medium">5d / 15d / 30d</th>
                </tr>
              </thead>
              <tbody>
                {predictions.map((p) => {
                  const pv = verdictStyles[p.verdict] ?? verdictStyles.WATCH;
                  return (
                    <tr key={p.id} className="border-t border-border">
                      <td className="px-4 py-2 text-muted">{formatWhen(p.created_at)}</td>
                      <td className={`px-4 py-2 font-semibold ${pv.text}`}>{p.verdict}</td>
                      <td className="px-4 py-2 font-mono">{confidencePct(p.confidence)}</td>
                      <td className="px-4 py-2 text-muted">{p.signal_alignment ?? "—"}</td>
                      <td className="px-4 py-2 font-mono text-xs text-muted">
                        {directionArrow(p.prediction_5d?.direction)}{" "}
                        {directionArrow(p.prediction_15d?.direction)}{" "}
                        {directionArrow(p.prediction_30d?.direction)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

function order(agent: string): number {
  return { technical: 0, fundamental: 1, arbitrator: 2 }[agent] ?? 9;
}

function BackLink() {
  return (
    <Link href="/" className="text-xs text-muted hover:text-white">
      ← all signals
    </Link>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-bg/50 p-4">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 text-sm text-white/90 ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}
