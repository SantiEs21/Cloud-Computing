"""Decoder API + page. Run from the repo root: uvicorn decoder.main:app --reload"""
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from supabase import create_client

from decoder.matching import Sample, match, video_samples

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")
db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
# pHash threshold in bits; comes from eval/metric_study.py (default 10 until the evaluation runs)
THRESHOLD = json.loads((HERE / "thresholds.json").read_text())["phash"]

app = FastAPI(title="Dashcam decoder")


def fetch_all(make_query) -> list[dict]:
    """Supabase returns at most 1000 rows per request, so read in pages."""
    rows, start = [], 0
    while True:
        page = make_query().range(start, start + 999).execute().data
        rows += page
        if len(page) < 1000:
            return rows
        start += 1000


def stored_samples(trip_id: str | None) -> dict[str, list[Sample]]:
    """Stored fingerprints grouped by trip (one trip, or all trips if trip_id is empty)."""
    def q():
        query = db.table("fingerprints").select("trip_id,t_ms,phash")
        if trip_id:
            query = query.eq("trip_id", trip_id)
        return query.order("trip_id").order("t_ms")
    by_trip: dict[str, list[Sample]] = {}
    for r in fetch_all(q):
        by_trip.setdefault(r["trip_id"], []).append(Sample(r["t_ms"], r["phash"]))
    return by_trip


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/trips")
def trips():
    return db.table("trips").select("id,driver_id,started_at").order("started_at", desc=True).execute().data


@app.post("/api/verify")
async def verify(video: UploadFile, trip_id: str = Form("")):
    t0 = time.perf_counter()
    data = await video.read()

    # 1) Exact check: is this file byte-for-byte a recorded segment?
    sha = hashlib.sha256(data).hexdigest()
    exact = db.table("segments").select("trip_id,seq,t_start_ms").eq("sha256", sha).execute().data

    # 2) Perceptual hashes of the uploaded video (OpenCV needs a file path; delete=False for Windows)
    tmp = tempfile.NamedTemporaryFile(suffix=Path(video.filename or "v.webm").suffix, delete=False)
    try:
        tmp.write(data)
        tmp.close()
        query = video_samples(tmp.name)
    finally:
        os.remove(tmp.name)
    t_hash = time.perf_counter()
    if not query:
        raise HTTPException(400, "Could not read any frame from the video")

    # 3) Sliding-window match against the chosen trip, or against every trip (best one wins)
    results = []
    for tid, stored in stored_samples(trip_id or None).items():
        r = match(query, stored, THRESHOLD)
        results.append({"trip_id": tid, **r})
    if not results:
        raise HTTPException(404, "No stored fingerprints for this trip")
    best = max(results, key=lambda r: (r["matched_pct"], -(r["mean_distance"] or 99)))
    t_end = time.perf_counter()

    return {
        **best,
        "threshold": THRESHOLD,
        "sha256": sha,
        "exact_match": [e for e in exact if e["trip_id"] == best["trip_id"]] or exact,
        "trips_compared": len(results),
        "video_duration_s": round(query[-1].t_ms / 1000 + 0.5, 1),
        "time_ms": {
            "hashing": round((t_hash - t0) * 1000),
            "matching": round((t_end - t_hash) * 1000),
            "total": round((t_end - t0) * 1000),
        },
    }


@app.post("/api/purge")
def purge(hours: int = Form(24)):
    return db.rpc("purge_expired", {"hours": hours}).execute().data


# The page (declared last so /api routes take precedence)
app.mount("/", StaticFiles(directory=HERE / "static", html=True), name="static")
