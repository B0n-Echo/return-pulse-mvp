import os

import psycopg
from dotenv import load_dotenv

# Load settings from .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn() -> psycopg.Connection:
    """Open a connection to the Return Pulse Postgres database.

    Returns:
        An open psycopg connection. Use it in a `with` block so it closes itself.

    Raises:
        RuntimeError: if DATABASE_URL is missing from .env.
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env.")
    return psycopg.connect(DATABASE_URL)


def get_counts() -> dict:
    """Count the returns in the database and how many have been classified.

    Returns:
        {"returns": all returns, "other": returns marked "Other",
         "classified": returns the pipeline has already labelled}
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM returns_enriched")
        total = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM returns WHERE reason_dropdown = 'Other'")
        other = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM classified_returns")
        classified = cur.fetchone()[0]
    return {"returns": total, "other": other, "classified": classified}
