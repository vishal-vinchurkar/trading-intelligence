# eval/

How we measure quality. Two things matter for this system:

1. **Schema validity** — every agent output must parse and match its schema
   (the JSON-enforcement rule). `validate.py` checks this.
2. **Agent isolation** — the technical output must contain no fundamental
   fields, and vice versa. `validate.py` checks this too.

Later, once predictions mature, **directional accuracy** of the 5/15/30-day
calls is measured from the `outcomes` table in Supabase (see schema.sql).

Run:
```bash
PYTHONPATH=. python eval/validate.py AAPL --no-save
```
