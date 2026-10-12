# Recommendations

Improvements we found while building Return Pulse. Each one costs money or changes how the team works, so it is Dhaga's decision, not ours.

---

## 1. Spot-check the cheap model with the stronger model

**What we found.** The cheap model reports almost the same confidence (about 0.9) on every answer, including the wrong ones. In a 50-return sample, every real reason scored between 0.8 and 1.0, and none of the 5 wrong answers scored below that. So the model's own confidence cannot tell us when it is wrong, and our "second opinion below 0.75" rule will rarely be triggered.

**What we recommend.** On every run, send a random 5% of the cheap model's answers to the stronger model as well:

- If both agree, keep the answer (it is now double-checked).
- If they disagree, use the stronger model's answer and flag it for review.
- Show the disagreement rate in every run report: a real quality number on real data, with no answer key needed.

**What it costs.** About 140 extra calls per full run of today's volume, roughly ₹20.

**What it gives you.** A measured answer to "how do we know it's right?", every week, instead of trusting the model's own confidence.

---

## 2. Decide which reasons count as vendor hotspots

**What we found.** The hotspot list includes groups like "Hawa Mahal Hand Block, kurti, size M: changed mind, 2.9× normal". "Changed mind" and "delivery late" aren't usually something a vendor can fix, so they may distract from fixable problems like fit, colour and quality.

**What we recommend.** Agree with the Category team which reasons belong in vendor hotspots. One option is to show only product-related reasons (too small, too large, colour mismatch, quality, damaged), and keep delivery issues in the Locations view.

**What it costs.** Nothing; it's a one-line rule change.
