# Return Pulse: sample data

**All data in this folder is synthetic.** No real Dhaga & Co. customer, order or return is included. It is shaped like Dhaga's real data, so the tool is tested on realistic input: return comments in Hinglish with typos, vague answers and mixed reasons; colour typed many different ways; free-text fabric; and size charts that differ by vendor.

A few patterns have been deliberately planted, so the dashboard has real signals to find and its results can be checked.

## Files

| File | What it does |
|---|---|
| `sql/01_schema.sql` | Creates the tables. **Re-running it drops and recreates them.** |
| `sql/02_data.sql` | Inserts the sample rows, in one transaction |
| `generate_data.py` | Rebuilds both SQL files and a `csv/` copy. The seed is fixed, so the output is always identical |

## Load into Postgres

```bash
createdb dhaga
psql -v ON_ERROR_STOP=1 -d dhaga -f data/sql/01_schema.sql
psql -v ON_ERROR_STOP=1 -d dhaga -f data/sql/02_data.sql
psql -d dhaga -c "SELECT count(*) FROM returns_enriched;"   # expect 6571
```

## Tables

| Table | What it holds |
|---|---|
| `returns` | Every return: dropdown reason, "Other" free text, return date |
| `orders` | Order date, payment mode, status (including RTO) and delivery city |
| `order_items` | Products in each order, with the size bought |
| `products` | Catalogue: category, vendor, colour, fabric |
| `vendors` | Suppliers |
| `customers`, `reviews` | Context only; not used by the MVP |
| `eval_return_labels` | The correct reason for each return, used **only** to measure classifier accuracy. It is never sent to a model |
| `classified_returns`, `weekly_issue_counts`, `corrections`, `settings` | Written by Return Pulse |
| `returns_enriched` (view) | Each return joined to its size, product, vendor and city. **This is the tool's main input** |

## How it compares with Dhaga's real figures

| | Dhaga | Sample data |
|---|---|---|
| Cash on delivery share | 61% | 61% |
| Cash-on-delivery orders that become RTO | 26% | 27% |
| Delivered orders with a return | 31% | 32% |
| Returns marked "Other" | 44% | 45% |
| Average order value | ₹840 | ₹924 |
| Volume | ~48,000 orders a week | 24,000 orders over two years (scaled down) |
