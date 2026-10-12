# Build note

How Return Pulse is built, what it costs, and what surprised us.

## 1. Code or model, step by step

A model earns its place only on messy language. Lookups, arithmetic and checks are plain code.

| Step | Code or model | Why |
|---|---|---|
| Fetch returns with no saved result | Code (SQL) | A lookup |
| Use the dropdown reason when the customer picked one | Code | Already clear, so a model would add cost and nothing else |
| Mark empty or junk comments "unclear" | Code | Nothing to read |
| Read each "Other" comment and pick 1 of 9 reasons, with a confidence and the supporting words | **Cheap model** (gpt-4o-mini), temperature 0 | Hinglish, typos and vague phrasing need language understanding |
| Second opinion on failed or low-confidence answers | **Strong model** (gpt-4o), temperature 0 | Judgment on the hardest cases, paid for only where needed |
| Check the quoted words appear in the comment (typo-tolerant) | Code | A text comparison; flags made-up evidence |
| Save results; count reasons by week, vendor, product, size and city | Code (SQL) | Storage and arithmetic |
| Hotspots and locations: share vs normal share, minimum sample | Code (SQL) | Arithmetic |
| Dashboard | Code | Reads stored results only, so no model runs when someone opens it |

**Temperatures.** Both models run at 0 because this is classification: the same comment should always get the same answer. Nothing in the product is customer-facing, so there is no step that needs a warmer, more varied tone.

**Structured output.** Every model call must return a validated schema (`ReturnReason`: reason from a fixed list of 9, confidence 0–1, evidence phrase). A malformed answer is retried once; if it fails again, the return is saved as `failed` and shown on the dashboard. A network error on one call marks that comment `failed` instead of stopping the run.

## 2. Why each pattern is there

**Parallelization: the cheap model reads 10 comments at a time.**
About 2,800 comments need reading. One at a time, that is close to an hour; in parallel, the full run took 5 minutes. Without it, the weekly job becomes slow enough that a failed run can't simply be re-run the same morning.

**Routing: each comment takes the cheapest path that can handle it.**
Dropdown and junk returns skip the AI entirely (57% of returns, at zero AI cost). AI answers that failed, or that give a real reason with confidence below 0.75, go to the strong model. Without routing, we would either pay the strong model for everything (about 15× the cost) or accept every shaky answer.

**Honest result:** the routing to the strong model fired only 19 times in 2,830 AI answers, because the cheap model reports about 0.9 confidence even when it is wrong (see section 4).

## 3. Cost line

Prices: gpt-4o-mini $0.15 / $0.60 and gpt-4o $2.50 / $10.00 per million input / output tokens; ₹88 per $ (assumption).

| | Arithmetic | Result |
|---|---|---|
| Full run (measured) | 2,811 cheap-model reads + 19 second opinions | **₹32.45** (cheap ₹29.20, strong ₹3.25) |
| Cost per AI-read comment | ₹32.45 ÷ 2,830 | **≈ ₹0.0115** |
| Comments needing AI at Dhaga's volume | 14,880 returns/week × 44% "Other" = 6,547, minus ~4% junk | **≈ 6,290 a week** |
| Weekly cost | 6,290 × ₹0.0115 | **≈ ₹72 a week** |
| Yearly cost | ₹72 × 52 | **≈ ₹3,750 a year** |

Opening the dashboard costs nothing. Most of each call's cost is our ~650-token instruction, not the comment, so a shorter prompt is the main lever if cost ever matters. The proposed 5% spot check would add about ₹20 per full run (see [recommendations](recommendations.md)).

## 4. What broke that we didn't expect

**The model's confidence isn't a measurement.** We planned to send answers below 75% confidence to the strong model. In practice, the cheap model said ~0.9 on almost every real reason, including the wrong ones ("ordered pink, got peach" was called wrong item at 0.9). So the second opinion almost never triggers. We kept the rule, documented the limit, and recommended a random 5% spot check instead, since that spending is the client's decision.

**An exact evidence check threw away correct answers.** We first required the quoted words to appear exactly. On the 200-comment test, 3 of the 4 "missing" quotes were correct answers where the model had quietly fixed the customer's typo ("pasad" → "pasand"). We switched to a typo-tolerant match (80% similarity), and we now flag a failed check instead of overwriting the answer.

**Our own answer sheet was wrong once, and our prompt contradicted itself once.** "Acha nahi laga" (didn't like it) was labelled unclear; it is a real reason, changed mind. And our first prompt let "different colour" count as both wrong item and colour mismatch. The test caught both.

**The database looked empty right after loading it.** After copying data to Neon through its pooled address, every query said the tables didn't exist. The data dump temporarily clears the table search path, and the connection pooler reused that same connection for the next query. The fix was to use the direct (non-pooled) address, which the live app now uses too.

## 5. Limits

- Accuracy (94% on 200 comments; 93% across all AI-read returns) was measured on synthetic comments we generated, and some prompt examples resemble them. Real accuracy is likely lower; the real check is a labelled sample of Dhaga's comments.
- The strong model scored 79% on its 19 cases: these are the genuinely hard comments, and a second opinion is not a guarantee.
- The pipeline runs as a script; in production, it would run on a nightly schedule owned by Dhaga's team.
