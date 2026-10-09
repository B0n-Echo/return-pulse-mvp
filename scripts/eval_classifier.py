"""Measure how well the cheap model classifies "Other" return comments.

Run from the repo root:
    python scripts/eval_classifier.py           # all 200
    python scripts/eval_classifier.py --n 10    # quick, cheap check first

Sends only the comment text to the model, scores the answers against the
answer sheet, prints a report with cost, and saves reports/classifier-eval.md
(readable) and reports/classifier-eval.json (full detail).
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so we can import rp_data and rp_workflow

from rp_data import get_eval_sample  # noqa: E402
from rp_workflow import CHEAP_MODEL, classify_comment  # noqa: E402

# ── Part 1: setup ───────────────────────────────────────────────────────────
PRICE_IN_USD = 0.15     # per 1M input tokens, gpt-4o-mini (check OpenRouter's current price)
PRICE_OUT_USD = 0.60    # per 1M output tokens
USD_TO_INR = 88         # assumption, for showing cost in rupees
OTHER_PER_WEEK = 6547   # Dhaga: 14,880 returns/week × 44% "Other"

PASS_ACCURACY = 0.80          # at least 80% right
MAX_WRONGLY_UNCLEAR = 0.10    # at most 10% of real reasons wrongly called unclear

REPORT_DIR = ROOT / "reports"
JSON_FILE = REPORT_DIR / "classifier-eval.json"
MD_FILE = REPORT_DIR / "classifier-eval.md"


def is_correct(pred: str, row: dict) -> bool:
    """Right if the model picked the true reason, or either reason for a mixed comment."""
    if pred == row["true_issue"]:
        return True
    return bool(row["is_mixed"]) and pred == row["true_secondary_issue"]


def write_markdown_report(summary: dict, path: Path) -> None:
    """Write a readable test report (shown nicely on GitHub).

    Args:
        summary: the saved results (same content as the JSON file).
        path: where to write the .md file.
    """
    s = summary
    lines = [
        "# Classifier evaluation",
        "",
        f"**Date:** {s['date']} · **Model:** `{s['model']}` · **Comments tested:** {s['n']}",
        "",
        f"## Verdict: {s['verdict']}",
        f"Pass rule: accuracy ≥ {PASS_ACCURACY:.0%} and wrongly-unclear ≤ {MAX_WRONGLY_UNCLEAR:.0%}.",
        "",
        "| Measure | Result |",
        "|---|---|",
        f"| Accuracy | {s['accuracy']:.0%} |",
        f"| Wrongly 'unclear' (real reason, model said unclear) | {s['wrongly_unclear']:.0%} |",
        f"| Failed (bad answer format twice) | {s['failed']} |",
    ]
    if s["mixed_accuracy"] is not None:
        lines.append(f"| Comments with two reasons | {s['mixed_accuracy']:.0%} |")
    lines += ["", "## By reason", "", "| Reason | Right | Total | Accuracy |", "|---|---|---|---|"]
    for issue, v in sorted(s["per_issue"].items(), key=lambda x: -x[1]["total"]):
        lines.append(f"| {issue} | {v['right']} | {v['total']} | {v['right'] / v['total']:.0%} |")
    lines += [
        "", "## Cost", "",
        f"- Tokens: {s['tokens_in']:,} in, {s['tokens_out']:,} out",
        f"- This run: ${s['cost_usd']:.4f} (≈ ₹{s['cost_usd'] * USD_TO_INR:.2f})",
        f"- At Dhaga's volume ({OTHER_PER_WEEK:,} 'Other' comments a week): ≈ ₹{s['cost_per_week_inr']:.0f} a week",
        f"- Prices: ${PRICE_IN_USD} / ${PRICE_OUT_USD} per 1M input / output tokens; ₹{USD_TO_INR} per $ (assumption)",
    ]
    wrong = [r for r in s["results"] if not r["correct"]]
    if wrong:
        lines += ["", f"## Wrong answers ({len(wrong)})", "", "| Comment | Model said | Should be |", "|---|---|---|"]
        for r in wrong:
            text = r["other_text"].replace("|", "/")
            lines.append(f"| {text} | {r['issue_type']} | {r['true_issue']} |")
    lines += [
        "", "## Limits of this test", "",
        "- Run on **synthetic** comments shaped like Dhaga's data, not real customer comments.",
        "- Some prompt examples resemble phrases in the test data, so real-world accuracy is likely lower.",
        "- The real check is a labelled sample of Dhaga's actual \"Other\" comments.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """Run the test, print the report and save the results."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200, help="how many comments to test")
    n = parser.parse_args().n

    # ── Part 2: the run ─────────────────────────────────────────────────────
    sample = get_eval_sample(n)
    print(f"Testing {len(sample)} comments with {CHEAP_MODEL}\n")
    results = []
    for i, row in enumerate(sample, start=1):
        pred = classify_comment(row["other_text"])  # the answer sheet is NOT sent
        correct = is_correct(pred["issue_type"], row)
        results.append({**row, **pred, "correct": correct})
        mark = "✓" if correct else "✗"
        print(f"{i:>3}/{len(sample)} {mark} {pred['issue_type']:<16} {row['other_text'][:55]}")

    # ── Part 3: the scoring ─────────────────────────────────────────────────
    total = len(results)
    accuracy = sum(r["correct"] for r in results) / total

    had_reason = [r for r in results if r["true_issue"] != "unclear"]
    wrongly_unclear = (
        sum(r["issue_type"] == "unclear" for r in had_reason) / len(had_reason)
        if had_reason else 0.0
    )
    failed = sum(r["issue_type"] == "failed" for r in results)

    per_issue = defaultdict(lambda: [0, 0])  # true_issue -> [right, total]
    for r in results:
        per_issue[r["true_issue"]][0] += r["correct"]
        per_issue[r["true_issue"]][1] += 1

    mixed = [r for r in results if r["is_mixed"]]
    mixed_accuracy = sum(r["correct"] for r in mixed) / len(mixed) if mixed else None

    wrong = [r for r in results if not r["correct"]]

    # ── Part 4: the cost ────────────────────────────────────────────────────
    tokens_in = sum(r["tokens"]["input_tokens"] for r in results)
    tokens_out = sum(r["tokens"]["output_tokens"] for r in results)
    cost_usd = (tokens_in * PRICE_IN_USD + tokens_out * PRICE_OUT_USD) / 1_000_000
    cost_per_comment_inr = cost_usd / total * USD_TO_INR
    cost_per_week_inr = cost_per_comment_inr * OTHER_PER_WEEK

    # ── Part 5: report, verdict and save ────────────────────────────────────
    print("\n──────── REPORT ────────")
    print(f"Accuracy:           {accuracy:.0%}  ({sum(r['correct'] for r in results)}/{total})")
    print(f"Wrongly 'unclear':  {wrongly_unclear:.0%}  (real reason, but model said unclear)")
    print(f"Failed:             {failed}")
    if mixed_accuracy is not None:
        print(f"Mixed comments:     {mixed_accuracy:.0%}  ({len(mixed)} with two reasons)")

    print("\nBy reason (right / total):")
    for issue, (right, count) in sorted(per_issue.items(), key=lambda x: -x[1][1]):
        print(f"  {issue:<16} {right:>3}/{count:<3} {right / count:.0%}")

    print("\nCost:")
    print(f"  Tokens:           {tokens_in:,} in, {tokens_out:,} out")
    print(f"  This run:         ${cost_usd:.4f}  (≈ ₹{cost_usd * USD_TO_INR:.2f})")
    print(f"  Per comment:      ≈ ₹{cost_per_comment_inr:.4f}")
    print(f"  Per week at Dhaga ({OTHER_PER_WEEK:,} 'Other' comments): ≈ ₹{cost_per_week_inr:.0f}")

    if wrong:
        print(f"\nWrong answers ({len(wrong)}):")
        for r in wrong:
            print(f"  said {r['issue_type']:<16} should be {r['true_issue']:<16} | {r['other_text']}")

    passed = accuracy >= PASS_ACCURACY and wrongly_unclear <= MAX_WRONGLY_UNCLEAR
    verdict = "PASS" if passed else "RETHINK"
    print(f"\nVERDICT: {verdict}  (needs accuracy ≥ {PASS_ACCURACY:.0%} "
          f"and wrongly-unclear ≤ {MAX_WRONGLY_UNCLEAR:.0%})")

    summary = {
        "date": date.today().isoformat(),
        "model": CHEAP_MODEL,
        "n": total,
        "accuracy": accuracy,
        "wrongly_unclear": wrongly_unclear,
        "failed": failed,
        "mixed_accuracy": mixed_accuracy,
        "per_issue": {k: {"right": v[0], "total": v[1]} for k, v in per_issue.items()},
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
        "cost_per_week_inr": cost_per_week_inr,
        "verdict": verdict,
        "results": results,
    }
    REPORT_DIR.mkdir(exist_ok=True)
    JSON_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    write_markdown_report(summary, MD_FILE)
    print(f"Saved: {MD_FILE.relative_to(ROOT)} and {JSON_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
