# return-pulse-mvp

Return Pulse: AI tool that reads Hinglish return comments and shows a D2C fashion brand why products come back. FDE Academy hackathon project.

## Test results

**Classifier: 94% accuracy on 200 return comments (PASS)** · ≈ ₹65 a week at the client's volume
→ Full report: [reports/classifier-eval.md](reports/classifier-eval.md)

The report shows accuracy per reason, cost, every wrong answer, and the limits of the test (it was run on synthetic data). To re-run it, see [Run the classifier test](#run-the-classifier-test) below.

## Project documents

| Document | What it covers |
|---|---|
| [Discovery note](docs/discovery-note.md) | The problem we chose, the evidence, and why it ranks first |
| [Classifier test report](reports/classifier-eval.md) | How well the AI reads return comments, and what it costs |
| [Sample data](data/README.md) | The synthetic dataset and how to load it |

## Run the app

You need Python 3.10+ and a Postgres database with the sample data loaded (see [data/README.md](data/README.md)).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit DATABASE_URL if your Postgres user or database differs
uvicorn rp_api:app --reload
```

Open http://127.0.0.1:8000. You should see the number of returns in the database. If the database can't be reached, the page shows the reason in red.

## Run the classifier test

Add your OpenRouter key to `.env` (`OPENROUTER_API_KEY=...`), then:

```bash
python scripts/eval_classifier.py --n 10    # quick check, about ₹0.10
python scripts/eval_classifier.py           # full test on 200 comments, about ₹2
```

It prints the results and updates [reports/classifier-eval.md](reports/classifier-eval.md).
