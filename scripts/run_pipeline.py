"""Classify every return that hasn't been classified yet, and save the results.

Run from the repo root:
    python scripts/run_pipeline.py --limit 50   # small sample first
    python scripts/run_pipeline.py              # everything still left
    python scripts/run_pipeline.py --fresh      # wipe saved results and redo all
"""
import argparse
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so we can import rp_data and rp_workflow

from rp_data import (  # noqa: E402
    get_conn, get_returns_to_classify, get_setting, refresh_counts, save_classified,
)
from rp_workflow import run_pipeline  # noqa: E402

# USD per 1M tokens (input, output). Check OpenRouter's current prices.
PRICES = {
    "cheap": (0.15, 0.60),    # openai/gpt-4o-mini
    "strong": (2.50, 10.00),  # openai/gpt-4o
}
USD_TO_INR = 88  # assumption, for showing cost in rupees


def cost_inr(tokens: dict, model: str) -> float:
    """Turn a token count into rupees for the given model ("cheap" or "strong")."""
    if not tokens:
        return 0.0
    price_in, price_out = PRICES[model]
    usd = (tokens["input_tokens"] * price_in + tokens["output_tokens"] * price_out) / 1_000_000
    return usd * USD_TO_INR


def main() -> None:
    """Run the pipeline on unclassified returns, save results, print a short report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="only classify this many (for a sample run)")
    parser.add_argument("--fresh", action="store_true", help="delete saved results and redo all")
    args = parser.parse_args()

    if args.fresh:
        with get_conn() as conn:
            conn.execute("DELETE FROM classified_returns")
        print("Fresh run: deleted all saved results.")

    rows = get_returns_to_classify()
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        print("Nothing to do: every return is already classified.")
        return

    threshold = float(get_setting("confidence_threshold"))
    print(f"Classifying {len(rows)} returns (second-opinion threshold {threshold}) ...")

    start = time.time()
    results = run_pipeline(rows, threshold)
    saved = save_classified(results)
    count_rows = refresh_counts()   # recount once, for the dashboard
    seconds = time.time() - start

    by_source = Counter(r["source"] for r in results)
    by_reason = Counter(r["issue_type"] for r in results)
    failed = by_reason.get("failed", 0)
    flags = sum(r["evidence_found"] is False for r in results)

    cheap_cost = strong_cost = 0.0
    for r in results:
        if r["source"] == "cheap_model":
            cheap_cost += cost_inr(r["tokens"], "cheap")
        elif r["source"] == "strong_model":
            cheap_cost += cost_inr(r.get("tokens_cheap"), "cheap")  # the first try
            strong_cost += cost_inr(r["tokens"], "strong")

    left = len(get_returns_to_classify())

    print("\n──────── RUN REPORT ────────")
    print(f"Processed:      {saved} returns in {seconds:.0f} seconds")
    print("Settled by:")
    print(f"  dropdown                     {by_source.get('dropdown', 0):>5}   (free)")
    print(f"  junk check                   {by_source.get('gate', 0):>5}   (free)")
    print(f"  cheap model                  {by_source.get('cheap_model', 0):>5}")
    print(f"  strong model (2nd opinion)   {by_source.get('strong_model', 0):>5}")
    print("Reasons:")
    for reason, count in by_reason.most_common():
        print(f"  {reason:<28} {count:>5}")
    print(f"Failed:         {failed}")
    print(f"Evidence flags: {flags}   (quote not found in the comment)")
    print(f"Cost:           cheap ≈ ₹{cheap_cost:.2f} · strong ≈ ₹{strong_cost:.2f} · "
          f"total ≈ ₹{cheap_cost + strong_cost:.2f}")
    print(f"Still left:     {left} returns")
    print(f"Counts table:   {count_rows} rows refreshed for the dashboard")


if __name__ == "__main__":
    main()
