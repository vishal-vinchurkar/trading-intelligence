# PHASE B — grounding the signal (built to run in PARALLEL)

Goal: add the context the price-only score can't see — macro regime, fundamental
quality, and event risk — then let a hybrid arbitrator combine quant + context.
Most valuable for **India**, where price alone had **no** net edge.

> Honesty rule (non-negotiable): none of these are point-in-time backtestable on
> free data, so they are **current-state overlays** — they refine/contextualise a
> signal and can VETO or size it, but they are NEVER folded into the backtested
> quant score. The quant score stays price-only and pure.

---

## Why parallel, and how to not collide
Phase B splits into **3 independent producers** + **1 integrator**. The producers
touch *disjoint files* and only need to agree on their **output contract** (below).
Build producers in parallel; integrate last. The three rules that make parallel safe:

1. **Contract-first** — the JSON each module returns is frozen here. Build to it; don't renegotiate mid-stream.
2. **Git worktrees** — each session works in its own worktree/branch so file edits never clobber.
3. **Disjoint ownership** — each session owns specific files; nobody edits `quant/scan.py` or `agents/agent_arbitrator.py` until integration.

---

## Contracts (FROZEN — build to these)

### Stream 1 — Macro  →  `data/fetcher_macro.py`
```python
macro_context(market: str) -> {
  "regime": "EASING" | "NEUTRAL" | "TIGHTENING",   # derived from policy-rate trend, NOT guessed
  "policy_rate": float, "ten_year": float, "two_year": float | None,
  "curve_slope_bps": float | None,                  # 10y - 2y
  "fx": {"pair": "USDINR", "level": float, "trend": "STRONGER"|"WEAKER"|"FLAT"} | None,
  "as_of": "YYYY-MM-DD", "source": "FRED" | "yfinance"
}
```
US via FRED (`FRED_API_KEY` in `.env`): DFF/FEDFUNDS, DGS10, DGS2. India: FRED India long-rate series if available + `INR=X` via yfinance. Regime = sign of policy-rate change over ~6 months.

### Stream 2 — Fundamentals  →  `quant/quality.py` (+ surface existing fetcher fields)
```python
quality_score(fundamentals: dict) -> {
  "score": float,                 # 0-100, current-state only
  "components": {"valuation": {...}, "profitability": {...}, "growth": {...}, "leverage": {...}},
  "assessment": "CHEAP"|"FAIR"|"EXPENSIVE",
  "reasons": [str, ...]
}
```
The fetchers ALREADY return EV/EBITDA, PEG, ROE, margins, D/E, div yield — currently discarded at the prompt. Use them. NO new data cost.

### Stream 3 — Events  →  `data/events.py`
```python
event_context(symbol: str) -> {
  "next_earnings_date": "YYYY-MM-DD" | None,
  "days_to_earnings": int | None,
  "event_within_horizon": bool,        # earnings within ~15 trading days
  "flag": "EARNINGS_SOON" | "CLEAR"
}
```
yfinance `get_earnings_dates()` / `calendar` (free, works for US + India).

### Stream 4 — Hybrid arbitrator (INTEGRATION, do last)  →  `agents/agent_arbitrator.py` + `quant/scan.py`
Consumes quant score + technical + fundamental + the three contexts above. Produces the final verdict where:
- the **quant score** sets the base direction/conviction (it's the only backtested part),
- macro/quality/events can **downgrade conviction, veto, or widen bands** (e.g. EARNINGS_SOON → cut size; India BULLISH only if quality agrees, since price has no edge there),
- every override carries a **stated reason** (auditable, not vibes).
Then surface the new fields in `dashboard/` (macro chip, quality bar, earnings flag).

---

## Session assignment (two parallel sessions)
- **Session A — branch `phaseb/grounding`, worktree `../ti-phaseb-grounding`**
  Owns: `data/fetcher_macro.py` (Stream 1) + `data/events.py` (Stream 3). Both are data fetchers; related; self-contained. Write a tiny `__main__` smoke test in each.
- **Session B — branch `phaseb/fundamentals`, worktree `../ti-phaseb-fundamentals`**
  Owns: `quant/quality.py` (Stream 2) + widening the fundamental fields surfaced from `data/fetcher_us.py` / `data/fetcher_india.py` (additive only — don't change existing return keys, only add).
- **Integration — branch `phaseb/integrate` (after A + B merge to main)**
  Owns Stream 4. One session, holistic. Pulls A + B, wires the arbitrator + scan + dashboard.

Neither A nor B touches `quant/scan.py`, `agents/agent_arbitrator.py`, or `dashboard/` — that's integration's job.

## Worktree setup (already created — see below)
```bash
# from the main repo:
git worktree list                       # shows the two phaseb worktrees
cd ../ti-phaseb-grounding               # Session A works here
cd ../ti-phaseb-fundamentals            # Session B works here
# each worktree shares nothing runtime — set up once per worktree:
ln -s ../trading-intelligence/.venv .venv          # reuse the venv
ln -s ../trading-intelligence/data/cache data/cache # reuse the 10y cache
cp ../trading-intelligence/.env .env                # secrets (gitignored)
```
When a stream is done: commit on its branch, push, open a PR (or merge to main). Integration starts once both producer branches are on main.

## Definition of done per stream
- Module returns exactly its contract shape, JSON-serialisable (no numpy types).
- `__main__` smoke test prints a real result for one US + one India name.
- No edits outside owned files. No changes to the backtested quant score.

## The automated alternative
If you'd rather not run two chat windows: a single session can fan these out with
the **Workflow tool** (multi-agent orchestration) — say "ultracode" or "use a
workflow" to opt in. Producers run as parallel sub-agents against these same
contracts; integration runs after. Same decomposition, one driver.

---

## Session kickoff prompts (paste verbatim into each worktree's Claude Code window)

Open a Claude Code window whose working directory is the worktree, then paste.

### Session A — `../ti-phaseb-grounding`
> You're in the `phaseb/grounding` worktree of the Sovian quant project. Read `docs/HANDOFF.md` and `docs/PHASE-B-PLAN.md` in full first. You OWN Stream 1 (macro) + Stream 3 (events): build `data/fetcher_macro.py` and `data/events.py` to the FROZEN contracts, each with a `__main__` smoke test printing a real result for AAPL and RELIANCE.NS. Rules: (1) the venv is Python 3.9 — add `from __future__ import annotations` to any file using `|` unions; (2) outputs must be plain JSON-serialisable types, no numpy; (3) macro `regime` must be DERIVED from real rate data, never guessed; (4) do NOT edit any file outside the two you own — not `quant/scan.py`, `agents/`, or `dashboard/`; (5) when both smoke tests pass, commit on `phaseb/grounding` and push. Do not deploy.

### Session B — `../ti-phaseb-fundamentals`
> You're in the `phaseb/fundamentals` worktree of the Sovian quant project. Read `docs/HANDOFF.md` and `docs/PHASE-B-PLAN.md` in full first. You OWN Stream 2: build `quant/quality.py` (a current-state 0–100 fundamental quality score, to the FROZEN contract) and widen the fundamental fields surfaced by `data/fetcher_us.py` and `data/fetcher_india.py` — ADDITIVE ONLY (add keys; never rename/remove existing ones or you break the live pipeline). Include a `__main__` smoke test printing a real result for AAPL and RELIANCE.NS. Rules: (1) Python 3.9 → `from __future__ import annotations` for `|` unions; (2) JSON-serialisable outputs, no numpy; (3) HONESTY RULE — quality is a current-state overlay; do NOT fold it into the backtested score and do NOT touch `quant/score.py`; (4) don't edit anything outside your owned files; (5) when the smoke test passes, commit on `phaseb/fundamentals` and push. Do not deploy.

### Integration — `phaseb/integrate` (run AFTER A + B are merged to main)
> Both producer branches are merged to main. Read `docs/PHASE-B-PLAN.md` Stream 4. Wire the hybrid arbitrator (`agents/agent_arbitrator.py`): the price-only quant score sets base direction/conviction; macro/quality/events may downgrade, veto, or widen bands — each override with a stated reason. Pay special attention to India (no price edge → require quality agreement). Then surface the new fields in `quant/scan.py` and `dashboard/` (macro chip, quality bar, earnings flag), rebuild, deploy, and update `docs/HANDOFF.md`.
