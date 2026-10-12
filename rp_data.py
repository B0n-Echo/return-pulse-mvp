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
# Hotspot rule: a reason's share in a group is at least MIN_TIMES_NORMAL times its
# normal share, the group has at least min_returns returns, and at least
# MIN_ISSUE_RETURNS of them have that reason.
MIN_TIMES_NORMAL = 1.5
MIN_ISSUE_RETURNS = 5

_HOTSPOT_SQL = """
            WITH normal AS (            -- each reason's share across ALL returns
                SELECT issue_type,
                       sum(return_count)::numeric / sum(sum(return_count)) OVER () AS normal_share
                FROM weekly_issue_counts
                GROUP BY issue_type
            ),
            grp AS (                    -- each reason's count inside each group
                SELECT {cols}, issue_type, sum(return_count) AS issue_returns,
                       sum(sum(return_count)) OVER (PARTITION BY {cols}) AS group_returns
                FROM weekly_issue_counts
                GROUP BY {cols}, issue_type
            )
            SELECT {select_cols}, g.issue_type,
                   g.issue_returns::int, g.group_returns::int,
                   round(g.issue_returns / g.group_returns, 3)::float AS share,
                   round(n.normal_share, 3)::float AS normal_share,
                   round((g.issue_returns / g.group_returns) / n.normal_share, 1)::float AS times_normal
            FROM grp g
            JOIN normal n USING (issue_type)
            {extra_join}
            WHERE g.group_returns >= %(min_returns)s           -- enough returns to trust
              AND g.issue_returns >= %(min_issue)s             -- not just one or two odd returns
              AND g.issue_type NOT IN ('unclear', 'failed')    -- only real, fixable reasons
              AND (g.issue_returns / g.group_returns) >= n.normal_share * %(min_times)s
            ORDER BY times_normal DESC, g.issue_returns DESC
            LIMIT 25
"""
# Each function below is a shell: the route works, but answers
# "not built yet" until its TODO is filled in.


def refresh_counts() -> int:
    """Recount everything into weekly_issue_counts (run once after each pipeline run).

    Returns:
        How many count rows were written.
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM weekly_issue_counts")
        cur.execute(
            """
            INSERT INTO weekly_issue_counts
                (week_start, issue_type, vendor_id, subcategory, size, ship_city, return_count)
            SELECT e.week_start, c.issue_type, e.vendor_id, e.subcategory, e.size, e.ship_city,
                   count(*)
            FROM classified_returns c
            JOIN returns_enriched e USING (return_id)
            GROUP BY e.week_start, c.issue_type, e.vendor_id, e.subcategory, e.size, e.ship_city
            """
        )
        return cur.rowcount


def get_summary() -> dict:
    """Headline numbers: total returns, classified, and the share with a known reason."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM returns")
        total = cur.fetchone()[0]
        cur.execute(
            """
            SELECT count(*),
                   count(*) FILTER (WHERE issue_type = 'unclear'),
                   count(*) FILTER (WHERE issue_type = 'failed'),
                   count(*) FILTER (WHERE evidence_found = false)
            FROM classified_returns
            """
        )
        classified, unclear, failed, flags = cur.fetchone()
    known = classified - unclear - failed
    return {
        "total_returns": total,
        "classified": classified,
        "known_reason": known,
        "known_share": round(known / classified, 3) if classified else 0.0,
        "unclear": unclear,
        "failed": failed,
        "evidence_flags": flags,
    }


def get_drivers() -> list[dict]:
    """Each reason's number of returns and its share of all returns."""
    with get_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT issue_type,
                   count(*) AS returns,
                   round(count(*)::numeric / sum(count(*)) OVER (), 3)::float AS share
            FROM classified_returns
            GROUP BY issue_type
            ORDER BY returns DESC
            """
        )
        return cur.fetchall()


def get_hotspots(min_returns: int) -> list[dict]:
    """Vendor + product type + size groups where a reason is well above its normal share.

    Args:
        min_returns: ignore groups with fewer returns than this (too few to trust).
    """
    sql = _HOTSPOT_SQL.format(
        cols="vendor_id, subcategory, size",
        select_cols="g.vendor_id, v.vendor_name, g.subcategory, g.size",
        extra_join="JOIN vendors v ON v.vendor_id = g.vendor_id",
    )
    params = {"min_returns": min_returns, "min_issue": MIN_ISSUE_RETURNS, "min_times": MIN_TIMES_NORMAL}
    with get_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_locations(min_returns: int) -> list[dict]:
    """Cities where a reason is well above its normal share.

    Args:
        min_returns: ignore cities with fewer returns than this.
    """
    sql = _HOTSPOT_SQL.format(cols="ship_city", select_cols="g.ship_city", extra_join="")
    params = {"min_returns": min_returns, "min_issue": MIN_ISSUE_RETURNS, "min_times": MIN_TIMES_NORMAL}
    with get_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_trend() -> list[dict]:
    """Number of returns per reason per week, for the trend chart."""
    with get_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT week_start, issue_type, sum(return_count)::int AS returns
            FROM weekly_issue_counts
            GROUP BY week_start, issue_type
            ORDER BY week_start, issue_type
            """
        )
        return cur.fetchall()


def get_hotspot_comments(vendor_id: str, subcategory: str, size: str, issue_type: str) -> list[dict]:
    """The customer comments behind one hotspot, for the drill-down.

    Only AI-read comments are listed (dropdown returns have no comment to show).
    """
    with get_conn() as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT c.return_id, e.other_text, c.issue_type, c.confidence::float,
                   c.evidence_phrase, c.evidence_found, c.source
            FROM classified_returns c
            JOIN returns_enriched e USING (return_id)
            WHERE e.vendor_id = %s AND e.subcategory = %s AND e.size = %s
              AND c.issue_type = %s
              AND c.source IN ('cheap_model', 'strong_model')
            ORDER BY c.evidence_found NULLS FIRST, c.confidence, c.return_id
            LIMIT 50
            """,
            (vendor_id, subcategory, size, issue_type),
        )
        return cur.fetchall()


def save_correction(return_id: str, is_correct: bool,
                    corrected_issue: str | None, note: str | None) -> dict:
    """Save Neha's check on one label: right (✓) or wrong (✗), with the right reason.

    Raises:
        LookupError: if the return has no classified result to correct.
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT issue_type FROM classified_returns WHERE return_id = %s", (return_id,))
        row = cur.fetchone()
        if row is None:
            raise LookupError(f"Return {return_id} has no classified result.")
        cur.execute(
            """
            INSERT INTO corrections (return_id, model_issue_type, is_correct, corrected_issue, note)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (return_id, row[0], is_correct, corrected_issue, note),
        )
        correction_id = cur.fetchone()[0]
    return {"saved": True, "id": correction_id, "return_id": return_id,
            "model_issue_type": row[0], "is_correct": is_correct,
            "corrected_issue": corrected_issue}
