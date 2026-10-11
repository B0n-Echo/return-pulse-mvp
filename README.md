# Return Pulse

**An AI tool that reads Hinglish return comments and shows a fashion brand why products come back, and where.**

Built as a forward-deployed engineering (FDE) engagement during FDE Academy's Tech Track. The client, Dhaga & Co., is a composite D2C fashion brand: realistic numbers and people, but not a real company.

---

## The engagement in 30 seconds

We weren't given a problem statement. We were given a business: ₹310 crore GMV, 48,000 orders a week, customers in tier-2 and tier-3 cities writing in Hinglish, and eight people who each believed their problem was the urgent one.

| What we did as FDEs | Result |
|---|---|
| **Ranked the eight complaints on evidence**, not on who spoke loudest | Picked one problem, owned by the Category Head, and wrote down why before any code |
| **Tested the riskiest assumption first**, for ₹2 | Confirmed the AI can read messy return comments (94% correct) before building on it |
| **Kept AI out of anything plain code can do** | 57% of returns settled by simple rules at zero AI cost |
| **Designed for the client's volume and budget** | About ₹65 a week to classify every unreadable comment |
| **Left spending decisions to the client** | Improvements that cost money are written up as [recommendations](docs/recommendations.md), not built in |

→ The full reasoning, decision by decision: **[How we worked as FDEs](docs/decisions.md)**

## The problem we chose

> "Returns are thirty-one percent overall. When I read the Other box by hand, most of it is about fit, but I can only read a few hundred at a time." (Neha, Category Head)

Almost a third of orders come back, and for nearly half of those returns nobody can say why: the reason is free text, often in Hinglish, and nobody has time to read ~6,500 comments a week.

We ranked it above three other problems: cash-on-delivery refusals, "where is my order" tickets, and slow product listing. It has the largest volume, its answer sits in text that AI can genuinely read, and it's an internal tool, so nothing unsafe reaches customers. Why it ranks first, and why we didn't merge it with cash-on-delivery refusals: **[discovery note](docs/discovery-note.md)**.

## What we built

Each step is either plain code or a model call, chosen on purpose:

| Step | Done by | Why that choice |
|---|---|---|
| Use the dropdown reason when the customer picked one | Code | Already clear, so paying a model to re-read it wastes money |
| Mark empty or junk comments "unclear" | Code | Nothing to read |
| Read the remaining comments, 10 at a time | Cheap model (gpt-4o-mini) | Messy Hinglish is where a model earns its place; running in parallel turns an hour into minutes |
| Second opinion on failed or unsure answers | Strong model (gpt-4o) | Pay for the expensive model only where it can help |
| Check that the quoted evidence is really in the comment | Code | Catches made-up reasons; flags them instead of hiding them |
| Count reasons by vendor, product, size, city and week | Code (SQL) | Arithmetic is a job for a database, not a model |
| Dashboard: drivers, hotspots, locations, trend, drill-down | Code | *In progress* |

## Results so far

| Measure | Result |
|---|---|
| Classifier accuracy (200 comments) | **94%** · [full report](reports/classifier-eval.md) |
| Real reasons wrongly called "unclear" | 3% |
| Returns settled without AI | 57% |
| Sample pipeline run (50 returns) | 3 seconds, ₹0.22, 0 failures |
| Cost at the client's volume | ≈ ₹65 a week |

**What we're honest about:** these tests ran on synthetic comments we generated to match Dhaga's data, so real-world accuracy is likely lower. The model also reports ~90% confidence even when it's wrong, so its confidence can't be trusted alone. Our proposed fix is in the [recommendations](docs/recommendations.md).

## What we'd need from the client next

- A labelled sample of real "Other" comments, to measure accuracy on real data
- Confirmation of definitions, e.g. "didn't like it" counts as changed mind, and a colour different from the photo counts as colour mismatch
- A decision on the 5% spot check (about ₹20 a run)
- Read-only access to the returns and orders tables, to run weekly instead of from a file

## Status

| Part | Status |
|---|---|
| Discovery and problem ranking | Done |
| AI classifier + accuracy test | Done |
| Classification pipeline | Built; tested on a 50-return sample |
| Counting and API routes | Routes in place; logic in progress |
| Dashboard | In progress |
| Deployment | Not started |

## Project documents

| Document | What it covers |
|---|---|
| [How we worked as FDEs](docs/decisions.md) | The judgment calls behind the project, and the FDE principles they follow |
| [Discovery note](docs/discovery-note.md) | The problem we chose, the evidence, and why it ranks first |
| [Classifier test report](reports/classifier-eval.md) | How well the AI reads return comments, and what it costs |
| [Recommendations](docs/recommendations.md) | Improvements we suggest, with their cost, for the client to decide on |
| [Sample data](data/README.md) | The synthetic dataset and how to load it |

---

## Run it yourself

You need Python 3.10+, Postgres with the sample data loaded ([how](data/README.md)), and an OpenRouter API key for the AI steps.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your OpenRouter key; edit DATABASE_URL if needed
uvicorn rp_api:app --reload
```

Open http://127.0.0.1:8000. You should see the number of returns in the database. If the database can't be reached, the page says why, in red.

### Classify returns

```bash
python scripts/run_pipeline.py --limit 50   # small sample first, about ₹0.20
python scripts/run_pipeline.py              # everything still unclassified, about ₹30
```

Only returns without a saved result are processed, so a sample run is never paid for twice.

### Re-run the classifier test

```bash
python scripts/eval_classifier.py --n 10    # quick check, about ₹0.10
python scripts/eval_classifier.py           # full test on 200 comments, about ₹2
```

It updates [reports/classifier-eval.md](reports/classifier-eval.md).

## Repository map

| Path | What it is |
|---|---|
| `rp_workflow.py` | The AI step and the pipeline: models, prompt, routing, evidence check |
| `rp_data.py` | Database access: fetching returns, saving results, counting |
| `rp_api.py` | The web server and API routes |
| `frontend/` | The dashboard page |
| `scripts/` | Run the pipeline; run the accuracy test |
| `reports/` | Test results |
| `docs/` | Discovery note, decision log, recommendations |
| `data/` | Synthetic sample data and the database schema |
