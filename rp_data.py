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


def get_returns_to_classify() -> list[dict]:
    """Fetch every return that has no row in classified_returns yet.

    A return counts as "done" once it has a result saved, so a crashed run,
    a late return or a missed week is simply picked up next time.

    Returns:
        A list of dicts: return_id, reason_dropdown, other_text.
    """
    with get_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT r.return_id, r.reason_dropdown, r.other_text
            FROM returns r
            WHERE NOT EXISTS (
                SELECT 1 FROM classified_returns c WHERE c.return_id = r.return_id
            )
            ORDER BY r.return_id
            """
        )
        return cur.fetchall()


def get_setting(key: str) -> str:
    """Read one value from the settings table, e.g. "confidence_threshold".

    Raises:
        KeyError: if the setting does not exist.
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
        row = cur.fetchone()
    if row is None:
        raise KeyError(f"Setting '{key}' not found in the settings table.")
    return row[0]


def save_classified(results: list[dict]) -> int:
    """Save pipeline results to classified_returns.

    If a return already has a row (a deliberate re-run), it is replaced.

    Args:
        results: dicts from run_pipeline().

    Returns:
        How many rows were saved.
    """
    rows = [
        (r["return_id"], r["issue_type"], r["confidence"], r["evidence_phrase"],
         r["evidence_found"], r["source"], r["model_name"])
        for r in results
    ]
    with get_conn() as conn, conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO classified_returns
                (return_id, issue_type, confidence, evidence_phrase,
                 evidence_found, source, model_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (return_id) DO UPDATE SET
                issue_type = EXCLUDED.issue_type,
                confidence = EXCLUDED.confidence,
                evidence_phrase = EXCLUDED.evidence_phrase,
                evidence_found = EXCLUDED.evidence_found,
                source = EXCLUDED.source,
                model_name = EXCLUDED.model_name,
                classified_at = now()
            """,
            rows,
        )
    return len(rows)


# ── Counting and dashboard queries (rp-05) ─────────────────────────────────
# Each function below is a shell: the route works, but answers
# "not built yet" until its TODO is filled in.


def refresh_counts() -> int:
    """Recount everything into weekly_issue_counts (run once after each pipeline run).

    Returns:
        How many count rows were written.
    """
    # TODO (you): empty weekly_issue_counts, then fill it from classified_returns
    #             joined to returns_enriched, grouped by week, reason, vendor,
    #             product type, size and city.
    raise NotImplementedError("refresh_counts")


def get_summary() -> dict:
    """Headline numbers: total returns, classified, and the share with a known reason."""
    # TODO (you)
    raise NotImplementedError("get_summary")


def get_drivers() -> list[dict]:
    """Each reason's number of returns and its share of all returns."""
    # TODO (you)
    raise NotImplementedError("get_drivers")


def get_hotspots(min_returns: int) -> list[dict]:
    """Vendor + product type + size groups where a reason is well above its normal share.

    Args:
        min_returns: ignore groups with fewer returns than this (too few to trust).
    """
    # TODO (you): the Vendor B rule: share in the group vs normal share (lift)
    raise NotImplementedError("get_hotspots")


def get_locations(min_returns: int) -> list[dict]:
    """Cities where a reason is well above its normal share.

    Args:
        min_returns: ignore cities with fewer returns than this.
    """
    # TODO (you): same rule as hotspots, grouped by city
    raise NotImplementedError("get_locations")


def get_trend() -> list[dict]:
    """Number of returns per reason per week, for the trend chart."""
    # TODO (you)
    raise NotImplementedError("get_trend")


def get_hotspot_comments(vendor_id: str, subcategory: str, size: str, issue_type: str) -> list[dict]:
    """The customer comments behind one hotspot, for the drill-down."""
    # TODO (you)
    raise NotImplementedError("get_hotspot_comments")


def save_correction(return_id: str, is_correct: bool,
                    corrected_issue: str | None, note: str | None) -> dict:
    """Save Neha's check on one label: right (✓) or wrong (✗), with the right reason."""
    # TODO (you)
    raise NotImplementedError("save_correction")
