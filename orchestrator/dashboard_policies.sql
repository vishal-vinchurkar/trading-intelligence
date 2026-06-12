-- Read-only RLS policies for the dashboard.
--
-- The Python pipeline writes with the SERVICE ROLE key (bypasses RLS). The
-- Next.js dashboard reads with the ANON key from the browser, so the read
-- tables need RLS enabled + a public SELECT policy. No INSERT/UPDATE/DELETE
-- policy is granted to anon, so the browser can never mutate data.
--
-- Run in the Supabase SQL editor after orchestrator/schema.sql.

ALTER TABLE tickers       ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_outputs ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcomes      ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read tickers"
  ON tickers FOR SELECT USING (true);

CREATE POLICY "public read predictions"
  ON predictions FOR SELECT USING (true);

CREATE POLICY "public read agent_outputs"
  ON agent_outputs FOR SELECT USING (true);

CREATE POLICY "public read outcomes"
  ON outcomes FOR SELECT USING (true);
