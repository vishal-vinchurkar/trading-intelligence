"""Eval: schema validity + agent isolation.

Runs the pipeline for a ticker and asserts:
  - each agent output has its required keys and enum values
  - the technical output leaks no fundamental fields, and vice versa

Exit code 0 = all checks pass, 1 = a check failed. Designed to be the
regression gate you can point to in interviews: "here's how I measure quality."
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from orchestrator.orchestrator import analyze

# Fields that must never appear in the *other* agent's output (isolation check).
FUNDAMENTAL_ONLY = {"valuation", "growth", "macro", "catalysts", "risks"}
TECHNICAL_ONLY = {"indicators", "key_levels"}

SIGNALS = {"BULLISH", "BEARISH", "NEUTRAL"}
VERDICTS = {"BUY", "SELL", "HOLD", "WATCH"}


def _check(name: str, condition: bool, failures: list[str]) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}")
    if not condition:
        failures.append(name)


def validate(result: dict) -> list[str]:
    failures: list[str] = []
    tech, fund, arb = result["technical"], result["fundamental"], result["arbitrator"]

    print("Schema:")
    _check("technical.signal is a valid enum", tech.get("signal") in SIGNALS, failures)
    _check("fundamental.signal is a valid enum", fund.get("signal") in SIGNALS, failures)
    _check("arbitrator.verdict is a valid enum", arb.get("verdict") in VERDICTS, failures)
    _check("arbitrator has a prediction block", isinstance(arb.get("prediction"), dict), failures)
    _check("arbitrator has reasoning", bool(arb.get("reasoning")), failures)

    print("Isolation:")
    _check(
        "technical output has no fundamental fields",
        not (FUNDAMENTAL_ONLY & set(tech.keys())),
        failures,
    )
    _check(
        "fundamental output has no technical fields",
        not (TECHNICAL_ONLY & set(fund.keys())),
        failures,
    )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate agent outputs for a ticker.")
    parser.add_argument("symbol")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    print(f"Running pipeline for {args.symbol}...\n")
    result = asyncio.run(analyze(args.symbol, save=not args.no_save))
    failures = validate(result)

    print()
    if failures:
        print(f"{len(failures)} check(s) failed: {failures}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
