# PITCH — Trading Intelligence System

> Source of truth for the public writeup. Revise as the build sharpens.

## The buyer in the room
Head of Product / Chief AI Officer at a fintech or brokerage — anyone who has to decide whether a multi-agent LLM system can produce *defensible, auditable* decisions, not just chat.

## The wedge — 12 words or fewer
Three blind AI analysts debate a stock; a fourth makes the call.

## The problem (1 paragraph)
Manual trading research is slow, biased, and incomplete. A technician ignores macro; a fundamental analyst misses momentum. Single-LLM "stock chatbots" launder both blind spots into one confident answer with no audit trail. The expensive failure mode isn't being wrong — it's being wrong *and* unable to say why, so you can't measure or improve it.

## What it does (1 paragraph)
For any US or Indian ticker, it runs two independent AI analysts in parallel — one sees only price action and technical indicators, the other only fundamentals and macro — deliberately blind to each other. A third, higher-capability arbitrator model receives both reports, identifies where they agree or conflict, weights them, and issues a structured verdict (BUY/SELL/HOLD/WATCH) with 5/15/30-day predictions and an explicit invalidation level. Every output is JSON, schema-validated, and stored — so each call is replayable and gradeable against what actually happened.

## The demo (3 bullets)
- **Setup** — type `RELIANCE.NS` (or `NVDA`); pipeline fetches live data, computes indicators, fires both analysts. The verdict lands as a card on the live dashboard (Next.js on Vercel, reading Supabase).
- **The "aha" moment** — open the ticker; the two analysts *disagree* (T·BEARISH vs F·NEUTRAL), and expanding the three agent panels shows each one's raw, schema-validated JSON — the arbitrator's reasoning explains exactly why it sided with one over the other. Visible reasoning, not a black box.
- **The close** — "Every verdict is stored with the data it was made on, and the dashboard shows the prediction history. How would your current research process prove the same?"

## Win condition
- **Schema validity ≥ 99%** of agent outputs parse and validate first or second try (the JSON-enforcement rule).
- **Agent isolation holds** — technical output contains zero fundamental fields and vice versa (testable in `eval/`).
- **Directional accuracy** of the 5-day call tracked in the `outcomes` table once predictions mature.

## What I'd build next with a real customer
Wire the arbitrator verdict to a paper-trading execution layer (Alpaca, $0) so the system doesn't just predict — it places the simulated trade and we measure realized P&L, not just direction.

## Publish artifact
- [ ] Repo public
- [ ] 60-second loom
- [ ] LinkedIn post draft (below)

---

## LinkedIn post draft

I built a stock-analysis system that does the opposite of what most "AI stock" tools do: instead of one model giving one confident answer, it forces three to disagree first.

Two AI analysts run in parallel on every ticker. One sees only the chart — RSI, MACD, moving averages, volume. The other sees only the business — valuation, growth, macro. They're structurally blind to each other. A third, larger model then arbitrates: it reads both reports, finds the conflict, picks a side, and — this is the part I care about — writes down *why* in a dissent field.

The point isn't the prediction. It's that every call is JSON, schema-validated, and stored with the exact data it was made on. So I can grade it. A stock chatbot can't tell you why it was wrong. This can.

Runs on free-tier models end to end. US and Indian markets. The next step is wiring it to paper trading so it's measured on realized P&L, not vibes.
