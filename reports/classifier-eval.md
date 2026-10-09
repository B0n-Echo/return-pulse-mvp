# Classifier evaluation

**Date:** 2026-10-09 · **Model:** `openai/gpt-4o-mini` · **Comments tested:** 200

## Verdict: PASS
Pass rule: accuracy ≥ 80% and wrongly-unclear ≤ 10%.

| Measure | Result |
|---|---|
| Accuracy | 94% |
| Wrongly 'unclear' (real reason, model said unclear) | 3% |
| Failed (bad answer format twice) | 0 |
| Comments with two reasons | 100% |

## By reason

| Reason | Right | Total | Accuracy |
|---|---|---|---|
| changed_mind | 39 | 45 | 87% |
| unclear | 30 | 32 | 94% |
| too_small | 30 | 30 | 100% |
| delivery_late | 24 | 24 | 100% |
| colour_mismatch | 19 | 22 | 86% |
| too_large | 19 | 19 | 100% |
| quality | 12 | 12 | 100% |
| damaged | 10 | 10 | 100% |
| wrong_item | 6 | 6 | 100% |

## Cost

- Tokens: 131,470 in, 4,643 out
- This run: $0.0225 (≈ ₹1.98)
- At Dhaga's volume (6,547 'Other' comments a week): ≈ ₹65 a week
- Prices: $0.15 / $0.6 per 1M input / output tokens; ₹88 per $ (assumption)

## Wrong answers (11)

| Comment | Model said | Should be |
|---|---|---|
| sir अच्छा नहीं लगा 🙏 | unclear | changed_mind |
| mam fnuction cancel ho gaya | delivery_late | changed_mind |
| sir अच्छा नहीं लगा 🙏 | unclear | changed_mind |
| function cncel ho gaya | unclear | changed_mind |
| bhaiya theekn ahi hai exchange nahi chahiye | changed_mind | unclear |
| bhaiya pink mangaya tha peach aaya refund chahiye | wrong_item | colour_mismatch |
| hello, same as before exchange nahi chahiye | changed_mind | unclear |
| mam अच्छा नहीं लगा very disappointed | unclear | changed_mind |
| mam colour fade sa hai photo jaisa nahi !! | quality | colour_mismatch |
| hello, colour fade sa hai photo jaisa nahi very disappointed | quality | colour_mismatch |
| function cancel ho gaya 🙏 | unclear | changed_mind |

## Limits of this test

- Run on **synthetic** comments shaped like Dhaga's data, not real customer comments.
- Some prompt examples resemble phrases in the test data, so real-world accuracy is likely lower.
- The real check is a labelled sample of Dhaga's actual "Other" comments.
