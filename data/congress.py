"""Congressional-trades data layer — pluggable adapters behind one interface.

The differentiator from the video: track what US members of Congress disclose
buying/selling and treat it as an alt-data overlay. The data is the hard part —
the free no-key mirrors (senate/house-stock-watcher S3) are now locked down, and
official House-Clerk filings expose only a filing INDEX for free (transaction
detail lives in PDFs). So this module is adapter-based:

  • QuiverAdapter   — Quiver Quantitative API (free tier, needs QUIVER_API_KEY).
                      The clean path: Quiver already parses the PDFs into rows.
  • HouseClerkAdapter — official free XML filing index (no key). Returns WHO filed
                      and WHEN, not parsed trades — full detail needs PDF parsing
                      (a later build). Useful as a freshness/coverage check.
  • DemoAdapter     — synthetic trades over the local price cache, so the signal +
                      backtest logic (quant.congress_signal) is testable with zero
                      credentials. Clearly labelled synthetic; never a real result.

Normalised record (CongressTrade): representative, ticker, transaction_date,
disclosure_date, txn_type ('buy'|'sell'), amount_low, amount_high.

Run:
  PYTHONPATH=. python -m data.congress            # auto-selects adapter, prints a sample
  PYTHONPATH=. python -m data.congress --demo     # force synthetic
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

from data import universe
from data.backfill import load_cached


@dataclass
class CongressTrade:
    representative: str
    ticker: str
    transaction_date: str   # ISO; when they traded
    disclosure_date: str    # ISO; when it became public — the only date you can act on
    txn_type: str           # 'buy' | 'sell'
    amount_low: float
    amount_high: float
    source: str             # which adapter produced it


# ---------------------------------------------------------------- Quiver (real)
QUIVER_URL = "https://api.quiverquant.com/beta/bulk/congresstrading"


def _quiver_available() -> bool:
    return bool(os.environ.get("QUIVER_API_KEY"))


def fetch_quiver(limit: int | None = None) -> list[CongressTrade]:
    key = os.environ.get("QUIVER_API_KEY")
    if not key:
        raise RuntimeError("QUIVER_API_KEY not set — get a free key at quiverquant.com")
    req = urllib.request.Request(
        QUIVER_URL,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    raw = json.load(urllib.request.urlopen(req, timeout=30))
    out = []
    for r in raw:
        ttype = (r.get("Transaction") or r.get("transaction") or "").lower()
        kind = "buy" if "purchase" in ttype or "buy" in ttype else "sell"
        amt = str(r.get("Range") or r.get("Amount") or "")
        lo, hi = _parse_amount_range(amt)
        out.append(CongressTrade(
            representative=r.get("Representative") or r.get("Name") or "?",
            ticker=(r.get("Ticker") or "").upper(),
            transaction_date=(r.get("TransactionDate") or r.get("Traded") or "")[:10],
            disclosure_date=(r.get("ReportDate") or r.get("Filed") or r.get("Disclosure") or "")[:10],
            txn_type=kind, amount_low=lo, amount_high=hi, source="quiver",
        ))
    out = [t for t in out if t.ticker and t.disclosure_date]
    return out[:limit] if limit else out


def _parse_amount_range(s: str) -> tuple[float, float]:
    """'$1,001 - $15,000' → (1001, 15000). Best-effort; 0,0 on failure."""
    nums = []
    for part in s.replace("$", "").replace(",", "").split("-"):
        part = part.strip()
        try:
            nums.append(float(part))
        except ValueError:
            pass
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], nums[0]
    return 0.0, 0.0


# ------------------------------------------------------- House Clerk (free idx)
HOUSE_CLERK_XML = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.xml"


def fetch_house_clerk_index(year: int) -> list[dict]:
    """Free, no-key filing INDEX (not parsed trades). FilingType 'P' = periodic
    transaction report (the stock trades) — detail is in a per-DocID PDF."""
    import xml.etree.ElementTree as ET

    req = urllib.request.Request(HOUSE_CLERK_XML.format(year=year),
                                 headers={"User-Agent": "Mozilla/5.0"})
    xml = urllib.request.urlopen(req, timeout=30).read()
    root = ET.fromstring(xml)
    rows = []
    for m in root.findall("Member"):
        def g(tag): el = m.find(tag); return el.text if el is not None else None
        rows.append({
            "name": f"{g('First') or ''} {g('Last') or ''}".strip(),
            "filing_type": g("FilingType"),
            "state_dst": g("StateDst"),
            "year": g("Year"),
            "filing_date": g("FilingDate"),
            "doc_id": g("DocID"),
            "ptr_pdf": f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{g('Year')}/{g('DocID')}.pdf"
                       if g("FilingType") == "P" else None,
        })
    return rows


_PTR_PAT = __import__("re").compile(
    r"\(([A-Z]{1,5})\)\s*\[ST\]\s*([PSE])\s*(\d{2}/\d{2}/\d{4})\s*(\d{2}/\d{2}/\d{4})"
    r"\s*[\$]([\d,]+)\s*-\s*[\$]?([\d,]+)"
)
PTR_CACHE = Path(__file__).parent / "cache"


def _parse_ptr_text(text: str) -> list[dict]:
    """Extract stock ([ST]) transactions from a House PTR's text.

    Line shape: `<owner> AssetName (TICKER) [ST] <P|S|E> <txnDate><notifDate><$lo - $hi>`.
    P = purchase (buy), S = sale (sell), E = exchange (skipped). Options/other asset
    types are ignored — equities only."""
    import re

    flat = re.sub(r"\s+", " ", text.replace("\x00", ""))
    out = []
    for tk, typ, td, _nd, lo, hi in _PTR_PAT.findall(flat):
        if typ == "E":
            continue
        out.append({
            "ticker": tk, "txn_type": "buy" if typ == "P" else "sell",
            "transaction_date": _us_to_iso(td),
            "amount_low": float(lo.replace(",", "")), "amount_high": float(hi.replace(",", "")),
        })
    return out


def _us_to_iso(s: str) -> str:
    from datetime import datetime
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return s


def fetch_house_clerk(years: list[int], max_filings: int = 80, cache: bool = True) -> list[CongressTrade]:
    """REAL congressional stock trades from the free, no-key House Clerk PTR PDFs.

    Pulls each year's filing index, keeps periodic transaction reports (type 'P'),
    fetches + parses each PDF (capped + cached). Disclosure date = the index filing
    date (when it became PUBLIC — the only date you can act on); transaction date
    comes from the PDF. Partial coverage by design: handwritten/scanned PTRs won't
    parse, but that's an unbiased subset for a hypothesis test."""
    import io
    from pypdf import PdfReader

    trades: list[CongressTrade] = []
    for year in years:
        cache_fp = PTR_CACHE / f"congress_house_{year}.json"
        if cache and cache_fp.exists():
            for d in json.loads(cache_fp.read_text()):
                trades.append(CongressTrade(**d))
            continue

        year_trades: list[CongressTrade] = []
        ptrs = [r for r in fetch_house_clerk_index(year)
                if r["filing_type"] == "P" and r["doc_id"] and r["filing_date"]]
        for r in ptrs[:max_filings]:
            try:
                req = urllib.request.Request(r["ptr_pdf"], headers={"User-Agent": "Mozilla/5.0"})
                data = urllib.request.urlopen(req, timeout=20).read()
                text = " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
            except Exception:  # noqa: BLE001 — skip unfetchable/corrupt PDFs
                continue
            disc = _us_to_iso(r["filing_date"])
            for tx in _parse_ptr_text(text):
                year_trades.append(CongressTrade(
                    representative=r["name"], ticker=tx["ticker"],
                    transaction_date=tx["transaction_date"], disclosure_date=disc,
                    txn_type=tx["txn_type"], amount_low=tx["amount_low"],
                    amount_high=tx["amount_high"], source="house-clerk",
                ))
        if cache:
            PTR_CACHE.mkdir(exist_ok=True)
            cache_fp.write_text(json.dumps([asdict(t) for t in year_trades], indent=2))
        trades.extend(year_trades)
    return trades


def _house_clerk_available() -> bool:
    try:
        import pypdf  # noqa: F401
        return True
    except ImportError:
        return False


# ----------------------------------------------------------- Demo (synthetic)
def fetch_demo(n_per_name: int = 8) -> list[CongressTrade]:
    """Synthetic trades over the cached US price history so the pipeline is
    testable with no credentials. NOT REAL — for logic/wiring validation only."""
    reps = ["Rep. A. Demo", "Sen. B. Demo", "Rep. C. Demo"]
    out: list[CongressTrade] = []
    for k, sym in enumerate(universe.symbols("US")[:12]):
        df = load_cached(sym)
        if df is None or len(df) < 300:
            continue
        # space sample dates across the history; vary by index (no RNG in this env)
        step = max(len(df) // (n_per_name + 1), 20)
        for j in range(1, n_per_name + 1):
            i = j * step
            if i >= len(df):
                break
            tdate = df.index[i].date()
            ddate = tdate + timedelta(days=30 + (i % 15))  # realistic 30-45d disclosure lag
            out.append(CongressTrade(
                representative=reps[(k + j) % len(reps)],
                ticker=sym,
                transaction_date=tdate.isoformat(),
                disclosure_date=ddate.isoformat(),
                txn_type="buy" if (i + k) % 3 else "sell",
                amount_low=1001, amount_high=15000, source="demo-synthetic",
            ))
    return out


# -------------------------------------------------------------- selector
def fetch_trades(prefer_demo: bool = False, years: list[int] | None = None) -> tuple[list[CongressTrade], str]:
    """Pick the best available adapter. Returns (trades, source_label).

    Priority: Quiver (if key) → free House-Clerk PTR PDFs (real, no key) → demo."""
    if prefer_demo:
        return fetch_demo(), "demo-synthetic"
    if _quiver_available():
        try:
            return fetch_quiver(), "quiver"
        except Exception as e:  # noqa: BLE001
            print(f"[congress] Quiver fetch failed ({e}); trying House-Clerk.")
    if _house_clerk_available():
        try:
            yrs = years or [2024, 2023, 2022]
            trades = fetch_house_clerk(yrs)
            if trades:
                return trades, "house-clerk"
            print("[congress] House-Clerk returned no parseable trades; using demo.")
        except Exception as e:  # noqa: BLE001
            print(f"[congress] House-Clerk fetch failed ({e}); using demo.")
    return fetch_demo(), "demo-synthetic"


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    demo = "--demo" in sys.argv
    trades, source = fetch_trades(prefer_demo=demo)
    print(f"[congress] {len(trades)} trades from '{source}'. Sample:")
    for t in trades[:5]:
        print("  " + json.dumps(asdict(t)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
