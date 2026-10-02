# return-pulse-mvp

Return Pulse: AI tool that reads Hinglish return comments and shows a D2C fashion brand why products come back. FDE Academy hackathon project.

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
