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


def get_eval_sample(n: int = 200) -> list[dict]:
    """Fetch "Other" returns together with their correct answer, for testing.

    The same n comments come back on every run (sorted by a scrambled
    return ID), so results can be compared after the prompt changes.
    The correct answer is only for scoring. Never send it to a model.

    Args:
        n: how many comments to fetch.

    Returns:
        A list of dicts: return_id, other_text, true_issue,
        true_secondary_issue, is_mixed.
    """
    with get_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT r.return_id, r.other_text,
                   e.true_issue, e.true_secondary_issue, e.is_mixed
            FROM returns r
            JOIN eval_return_labels e USING (return_id)
            WHERE r.reason_dropdown = 'Other'
            ORDER BY md5(r.return_id)
            LIMIT %s
            """,
            (n,),
        )
        return cur.fetchall()
