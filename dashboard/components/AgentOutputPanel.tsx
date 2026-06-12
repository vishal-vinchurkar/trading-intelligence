"use client";

import { useState } from "react";
import type { AgentOutput } from "@/lib/types";

const AGENT_META: Record<string, { title: string; blurb: string }> = {
  technical: {
    title: "Agent 1 · Technical",
    blurb: "Price action & momentum only — blind to fundamentals.",
  },
  fundamental: {
    title: "Agent 2 · Fundamental",
    blurb: "Business quality, valuation & macro only — blind to price.",
  },
  arbitrator: {
    title: "Agent 3 · Arbitrator",
    blurb: "Sees both reports and makes the final call.",
  },
};

// Expandable raw agent JSON. The collapsed state shows the agent's headline
// signal + summary; expanding reveals the full validated JSON it produced —
// the "show your work" view that makes the multi-agent isolation auditable.
export function AgentOutputPanel({ output }: { output: AgentOutput }) {
  const [open, setOpen] = useState(false);
  const meta = AGENT_META[output.agent] ?? { title: output.agent, blurb: "" };
  const o = output.output as Record<string, unknown>;
  const headline =
    (o.verdict as string) || (o.signal as string) || "—";
  const summary = (o.summary as string) || (o.reasoning as string) || "";

  return (
    <div className="rounded-lg border border-border bg-panel">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div>
          <div className="flex items-center gap-2">
            <span className="font-semibold">{meta.title}</span>
            <span className="rounded bg-border px-1.5 py-0.5 text-[11px] font-mono text-muted">
              {headline}
            </span>
          </div>
          <div className="text-xs text-muted">{meta.blurb}</div>
        </div>
        <span className="text-muted text-sm">{open ? "▲" : "▼"}</span>
      </button>

      {summary && !open && (
        <p className="px-4 pb-3 text-sm text-muted">{summary}</p>
      )}

      {open && (
        <div className="border-t border-border px-4 py-3">
          {output.model_used && (
            <div className="mb-2 text-[11px] text-muted">
              model: <span className="font-mono">{output.model_used}</span>
            </div>
          )}
          <pre className="max-h-96 overflow-auto rounded bg-bg p-3 text-xs leading-relaxed text-muted">
            {JSON.stringify(output.output, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
