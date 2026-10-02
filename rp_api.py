from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from rp_data import get_counts

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

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
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "db_error", "detail": str(e)})


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def home() -> FileResponse:
    """Serve the Return Pulse page."""
    return FileResponse(FRONTEND_DIR / "index.html")
