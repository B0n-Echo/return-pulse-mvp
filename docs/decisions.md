# How we worked as forward-deployed engineers

A forward-deployed engineer (FDE) isn't handed a spec. We're dropped into a client's business, listen to people who disagree about what's wrong, decide which problem is worth solving, and build the smallest thing that proves it can be solved. Then we hand it to a team that has to run it on Monday.

This log shows that way of working on a real-shaped engagement with Dhaga & Co., a D2C fashion brand. Every entry is a judgment call: what we chose, what else we considered, and the evidence behind it. The technology mattered less than the decisions.

## The principles behind the decisions

| FDE principle | Where you can see it |
|---|---|
| **Find the problem before the solution.** Rank the client's complaints on evidence, not on who complains loudest. | 1, 2, 3 |
| **Test the riskiest assumption first.** Spend ₹2 to learn whether an idea works before spending days building it. | 7, 8 |
| **Use AI only where it earns its place.** Plain code for lookups, counting and checks; models only for messy language. | 11, 12, 18 |
| **Every rupee is the client's rupee.** Design for cost at their real volume, and leave spending decisions to them. | 12, 13, 17, 20 |
| **Let evidence overrule the plan.** When test data contradicted our design, we changed the design. | 9, 15, 17 |
| **Build for the team that runs it after we leave.** No ML engineer needed; settings change without code; nothing breaks silently. | 14, 16, 21 |
| **Be honest about limits.** Say what was estimated, what was synthetic, and what still needs the client's confirmation. | 6, 9, 21 |

---

## Choosing the problem
*The client gave us eight complaints, not a problem statement. Picking the right one was the first deliverable.*

**1. Fix unread return reasons first (owner: Neha, Category Head).**
We ranked four problems: unread return reasons, cash-on-delivery RTO, "where is my order" tickets, and slow sample-to-live. Return reasons came first. It has the largest volume (~14,880 returns a week), the answer sits in free text nobody reads (where AI genuinely helps), it's an internal tool (nothing unsafe reaches customers), and a small team can run it. Full reasoning: [discovery note](discovery-note.md).

**2. Treat RTO as a separate problem.**
RTO parcels are refused at the door and go back unopened, so there's no return reason to read, and fixing fit can't reduce refusals. Mixing the two would have overstated what the tool can do. RTO is #2 on our list.

**3. Neha owns it, not the Head of Supply Chain.**
The 31% return rate is Neha's number, and she is the one reading comments by hand today. Supply chain is a stakeholder: fewer returns means fewer reverse pickups.

## Shaping the product
*Build the smallest thing a real user can operate without us in the room.*

**4. An internal dashboard, not a chat.**
Neha's question is "what's the pattern across thousands of returns?". A dashboard shows that at a glance and gives the same answer every time. A chat could come later, on top of it.

**5. Load data from a file for the MVP; connect to live systems later.**
The MVP isn't meant to integrate with real platforms. The "get this week's returns" step is kept separate, so it can later read Dhaga's database on a schedule without changing anything else.

**6. Build and test on synthetic data shaped like Dhaga's.**
We had no access to real data. The sample data copies the real mess: Hinglish, typos, colour written 95 ways, vague comments. We say openly that results on it are likely better than on real comments.

## The AI step
*Prove the idea cheaply before building on it, and make the model's job as clear as possible.*

**7. Test the riskiest assumption before building anything big.**
Our biggest assumption was that the "Other" text contains a readable reason. We tested it on 200 comments first: 94% correct, so we went ahead. See the [test report](../reports/classifier-eval.md).

**8. Pass rule: at least 80% correct, and at most 10% wrongly called "unclear".**
We measure *wrongly* unclear, not all unclear, because about a sixth of comments are genuinely vague, and "unclear" is the right answer for them.

**9. "Acha nahi laga" (didn't like it) counts as changed mind, not unclear.**
It is a real reason. We corrected our answer sheet so the test didn't punish the model for a right answer. This is a definition to confirm with Neha.

**10. A colour different from the photo or order is colour mismatch; wrong item means a different product or design.**
The first prompt allowed both readings for "ordered pink, got peach". The two lead to different fixes (catalogue versus warehouse), and the dashboard's patterns can tell them apart later.

**11. Two models: a cheap one for everything, a strong one only for second opinions.**
gpt-4o-mini reads all comments; gpt-4o only re-checks failed or unsure answers. Both run at temperature 0 so the same comment always gets the same answer.

## The pipeline
*Design for the client's real volume and budget, and for the team that runs it after we leave.*

**12. Let plain code settle what it can, for free.**
Returns with a clear dropdown reason are copied as they are, and empty or junk comments become "unclear". That settles 57% of returns with no AI cost.

**13. Sort everything first, then send the AI pile ten at a time.**
One by one, ~2,900 comments would take close to an hour; in parallel, a few minutes.

**14. Second opinion below 75% confidence, stored in the settings table.**
Started at a sensible level, to be tuned on real data. It lives in the database so it can change without touching code. "Unclear" answers are trusted, because a vague comment stays vague whoever reads it.

**15. Typo-tolerant evidence check that flags rather than overwrites.**
In our test, 3 of the 4 quotes that didn't match exactly were correct answers where the model had fixed a customer's typo. So we accept close matches, and if a quote still isn't found, we keep the reason but flag it for review instead of throwing it away.

**16. A return "needs work" if it has no saved result, not by date.**
Dates miss returns when a run crashes or a return arrives late. Checking "is there a saved result?" can't miss anything. Re-running old returns is a deliberate, selective choice, never automatic.

**17. Spot-checking the cheap model is a recommendation, not a feature.**
The model reports about 0.9 confidence even when wrong, so a random 5% spot check by the strong model would be a better safety net. It costs money every run, so it's Dhaga's decision. See [recommendations](recommendations.md).

## Counting and the dashboard
*Turn labels into decisions Neha can act on, and never hide a gap.*

**18. Count once after each run and store the totals.**
The data changes weekly, so counting once and storing the totals keeps the dashboard instant and the database load low.

**19. A hotspot is a reason that is well above its normal share, with enough returns to trust.**
200 "too small" out of 2,000 (10%) is normal for a big seller; 60 out of 100 (60%) points to a real problem, such as a wrong size chart. Groups with fewer than 20 returns are ignored, because 2 out of 2 proves nothing.

**20. No "Analyse" button on the dashboard.**
Running the pipeline spends money, so it stays a deliberate script run, not a click.

**21. Fail visibly, everywhere.**
A red error when the database is down, "not built yet" for unfinished routes, and "unclear", "failed" and evidence flags shown on screen. A visible gap is better than a silent wrong answer.

**22. Lay out the dashboard in the order Neha asks her questions.**
How big is the problem? What's driving it? Where exactly (hotspots, with the comments behind them)? Which cities? Is it getting better? Big picture first, then problems, then detail.

**23. Build the screens before the backend, against agreed data shapes.**
We agreed what each route returns first, then built the screens against sample files of that shape. When a part of the server isn't ready, its section shows the sample data and is clearly labelled "Sample", so nobody mistakes it for real numbers.

**24. A hotspot must be at least 1.5× normal, with at least 5 returns giving that reason.**
"Well above normal" needed a number, so we started at 1.5×. Requiring 5 returns with the reason stops a group of 20 with just 2 odd returns from looking like a crisis: the same "2 out of 2 proves nothing" problem, one level down. Both are starting values, to be tuned once real results are on the dashboard.
