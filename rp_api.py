import logging
from pathlib import Path

from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rp_data import (
    get_counts, get_drivers, get_hotspot_comments, get_hotspots, get_locations,
    get_setting, get_summary, get_trend, save_correction,
)

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

log = logging.getLogger("return_pulse")

app = FastAPI(title="Return Pulse")


@app.get("/api/health")
def health():
    """Check the database is reachable and report the current counts.

    Returns:
        200 {"status": "ok", "counts": {...}} when the database answers,
        503 {"status": "db_error", "detail": reason} when it does not.
    """
    try:
        return {"status": "ok", "counts": get_counts()}
    except Exception:
        # Full technical error goes to the server log; the screen gets one plain sentence
        log.exception("Health check: database unreachable")
        return JSONResponse(status_code=503, content={
            "status": "db_error",
            "detail": "Can't reach the database right now. The data will appear once it's back.",
        })


@app.exception_handler(NotImplementedError)
def not_built_yet(request: Request, exc: NotImplementedError):
    """Answer 501 for routes whose logic isn't written yet, instead of a crash."""
    return JSONResponse(status_code=501, content={"detail": f"not built yet: {exc}"})


def min_returns() -> int:
    """The smallest group we trust for a hotspot, read from the settings table."""
    return int(get_setting("min_returns_per_hotspot"))


@app.get("/api/summary")
def summary():
    """Headline numbers for the top of the dashboard."""
    return get_summary()


@app.get("/api/drivers")
def drivers():
    """Each reason's share of all returns (the bar chart)."""
    return get_drivers()


@app.get("/api/hotspots")
def hotspots():
    """Vendor + product type + size groups with a reason well above normal."""
    return get_hotspots(min_returns())


@app.get("/api/locations")
def locations():
    """Cities with a reason well above normal."""
    return get_locations(min_returns())


@app.get("/api/trend")
def trend():
    """Returns per reason per week."""
    return get_trend()


@app.get("/api/hotspots/comments")
def hotspot_comments(vendor_id: str, subcategory: str, size: str, issue_type: str):
    """The customer comments behind one hotspot."""
    return get_hotspot_comments(vendor_id, subcategory, size, issue_type)


class CorrectionRequest(BaseModel):
    """Neha's check on one label."""
    return_id: str
    is_correct: bool
    corrected_issue: Optional[str] = None
    note: Optional[str] = None


@app.post("/api/corrections")
def corrections(body: CorrectionRequest):
    """Save a ✓ or ✗ on one label."""
    try:
        return save_correction(body.return_id, body.is_correct, body.corrected_issue, body.note)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def home() -> FileResponse:
    """Serve the Return Pulse page."""
    return FileResponse(FRONTEND_DIR / "index.html")
