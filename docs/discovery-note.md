# Discovery Note: Return Pulse

**Date:** 2026-10-02
**Client:** Dhaga & Co.
**Agreed by:** _[add the five team members' names before committing]_

Labels: **(brief)** = stated in the case study · **(calc)** = our arithmetic from brief numbers · **(inferred)** = our reasoning, to confirm with the client

---

## 1. The problem, in the client's words
>
> "Returns are thirty-one percent overall. When I read the Other box by hand, most of it is about fit, but I can only read a few hundred at a time." (Neha, Category Head)

Almost a third of orders come back, and for nearly half of those returns nobody can say why: the reason is sitting in free text that nobody has time to read.

## 2. Who owns it, and what they do instead today

**Owner: Neha, Category Head.** The 31% is her number, and she is doing the workaround: reading "Other" comments by hand, a few hundred at a time. The likely causes (fit, size charts, fabric, colour, product quality) sit with the products and the catalogue, which is where any fix gets made (inferred).
**Stakeholder: Faizan, Head of Supply Chain.** Fewer returns means fewer reverse pickups. His own complaint (RTO on cash on delivery) is a separate problem, ranked #2 below.

## 3. Evidence

- Returns are 31% overall. (brief, S05 Neha)
- 44% of returns land in "Other", which is free text. (brief, S04)
- Neha reads "Other" by hand and thinks most is fit, but only from a few hundred comments. (brief, S05)
- Catalogue data is messy: size charts differ per vendor, fabric is free text, and colour is typed ~90 ways. These are plausible causes of returns. (brief, S04)
- 410,000 reviews (18 months) are displayed but never analysed. (brief, S04)
- Order data (line items, address, status history) is clean and trustworthy, so returns can be sliced by SKU, vendor, size and city. (brief, S04)
- Customers write in Hinglish and search by occasion, so any free-text reading must handle Hinglish. (brief, S02, S06)

## 4. What it costs today

- ~14,880 returns per week (48,000 × 31%), ~7.7 lakh a year. (calc)
- ~6,547 returns per week with an unread reason (14,880 × 44%), against "a few hundred at a time" read by hand. (calc)
- ~₹1.25 crore of order value goes back each week (14,880 × ₹840 average order value), ~₹65 crore a year. (calc, estimate)
- Logistics cost per return: **not stated.** To ask the client.
- Repeat purchase is stuck at 22% (Ritu) and acquisition cost is up 40% (Sameer). If returns hurt repeat buying, this problem feeds both (inferred, see assumption 2).

## 5. What success looks like, and how we'd measure it

- **MVP (immediate):** the share of returns with a known reason goes from ~56% to ≥90%, and Neha can see the top reasons by SKU, vendor, size and city without reading by hand. Measured from the returns data they already hold.
- **Business (after acting on findings):** the return rate falls on the SKUs and vendors that were flagged and fixed, compared with their own earlier rate. Target agreed with Neha, not set by us.

## 6. Ranked shortlist

**Ranked on:** weekly cost or volume · a named owner losing something today · data that exists and suits language models · survives the constraints (no ML engineer, cost per action, safe output) · link to repeat purchase.

| # | Problem | Owner | Why it sits here |
|---|---|---|---|
| 1 | Unread return reasons | Neha | Largest volume (~14,880/week). The answer is in unread free text, which is where a model earns its place. Internal tool, so nothing unsafe is published. A small team can run it. |
| 2 | RTO on cash on delivery | Faizan | Most precisely costed: ~7,613 RTOs/week × ₹120 ≈ ₹4.75 crore/year (calc). But the core fix is scoring structured order data, which needs classic ML that Dev says they can't run. No reason text exists for RTO. |
| 3 | "Where is my order" tickets | Arpita | ~5,220 tickets/week (58% of ~9,000), 9-hour first response (calc, brief). No rupee cost given. The fix is mostly an order-status lookup, so code does the work, not a model. May be a symptom of tracking not being visible in the app (to ask). |
| 4 | Sample-to-live takes 6–9 days | Vivek | Drops are 3–4 days apart, so delays miss the Tuesday spike (brief). Impact not quantified, and auto-written product copy is customer-facing, so it needs review. |

Not ranked: repeat purchase (Ritu) and acquisition cost (Sameer). These are outcomes, the scoreboard, not problems you can fix directly.

## 7. Biggest assumption, and what would prove it wrong

**Assumption 1: the "Other" text contains a usable reason.** If most entries say things like "not good" or "don't want", there's nothing to classify.
*Proven wrong if:* on a sample of 200, most comments come back "unclear".

**Assumption 2: returns hurt repeat purchase.** This is the link that makes the problem matter to Ritu and Sameer.
*Proven wrong if:* in order history, customers whose first order was returned come back at the same rate as those whose wasn't.

---

**Questions for the client:**

- Who formally owns returns?
- What is the logistics cost per return?
- Is the 26% RTO counted inside the 31%?
- How much returns history exists (needed for year-over-year trends)?
- Does "RTO" mean refused or undelivered parcels, as in standard usage?
