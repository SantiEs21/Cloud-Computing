"""Matching of an uploaded video against the hashes stored for a trip.

1. Sample the video every 500 ms (by timestamp) and compute the pHash of each sample.
2. Sliding window: try many offsets (where the video starts inside the trip). For each offset, every
   query sample is compared with the stored sample closest in TIME (t_ms, not index: browser timers
   jitter). The offset with the lowest mean Hamming distance is the position in the trip.
3. A sample is "matched" if its distance <= threshold; >= 2 unmatched in a row = modified section.
"""
from bisect import bisect_left
from dataclasses import dataclass

import cv2

from decoder.fingerprint import hamming, phash

SAMPLE_MS = 500
MAX_GAP_MS = 600        # stored sample further away in time = "missing" (> 500 ms spacing: timer jitter, edges)
MISSING_DIST = 32       # distance used for missing samples (= two random 64-bit hashes)
MIN_RUN = 2             # consecutive unmatched samples that make a "modified section"


@dataclass
class Sample:
    t_ms: int
    phash: str


def video_samples(path: str, step_ms: int = SAMPLE_MS) -> list[Sample]:
    """One pHash every step_ms of video time. Frames are read sequentially (no seeking):
    browser-recorded webm files often have no index, so seeking is unreliable."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if 1 <= fps <= 120 else 15  # webm from MediaRecorder may report nonsense
    out, idx, next_t, last_t = [], 0, 0.0, -1.0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = cap.get(cv2.CAP_PROP_POS_MSEC)
        if t <= last_t:  # missing/broken timestamps -> derive from the frame number
            t = idx * 1000 / fps
        last_t = t
        if t >= next_t:
            out.append(Sample(int(round(t)), phash(frame)))
            next_t += step_ms
            while next_t <= t:  # skip sample slots with no frame (e.g. dropped frames)
                next_t += step_ms
        idx += 1
    cap.release()
    return out


def _nearest(stored_t: list[int], t: float) -> int | None:
    """Index of the stored sample closest in time to t, or None if none within MAX_GAP_MS."""
    i = bisect_left(stored_t, t)
    best = min((j for j in (i - 1, i) if 0 <= j < len(stored_t)), key=lambda j: abs(stored_t[j] - t), default=None)
    return best if best is not None and abs(stored_t[best] - t) <= MAX_GAP_MS else None


def distances(query: list[Sample], stored: list[Sample], offset: float, stored_t=None) -> list[int | None]:
    """Hamming distance of each query sample to the stored sample at (query time + offset)."""
    stored_t = stored_t or [s.t_ms for s in stored]
    out = []
    for q in query:
        j = _nearest(stored_t, q.t_ms + offset)
        out.append(None if j is None else hamming(q.phash, stored[j].phash))
    return out


def best_offset(query: list[Sample], stored: list[Sample]) -> tuple[float, float]:
    """Sliding window. Candidate offsets: the first query sample on every stored sample (video starts
    inside the trip) and the first stored sample on every query sample (video starts before the trip,
    e.g. extra frames at the start). Returns (offset_ms, mean distance)."""
    q0, s0 = query[0].t_ms, stored[0].t_ms
    candidates = {s.t_ms - q0 for s in stored} | {s0 - q.t_ms for q in query}
    stored_t = [s.t_ms for s in stored]
    best = (0.0, float(MISSING_DIST + 1))
    for off in candidates:
        d = distances(query, stored, off, stored_t)
        mean = sum(MISSING_DIST if x is None else x for x in d) / len(d)
        if mean < best[1]:
            best = (off, mean)
    return best


def sections(query: list[Sample], matched: list[bool]) -> list[tuple[float, float]]:
    """Runs of >= MIN_RUN unmatched samples -> (start_s, end_s) in video time."""
    out, start = [], None
    for i, ok in enumerate(matched + [True]):  # sentinel closes a trailing run
        if not ok and start is None:
            start = i
        elif ok and start is not None:
            if i - start >= MIN_RUN:
                end_t = query[i].t_ms if i < len(query) else query[-1].t_ms + SAMPLE_MS
                out.append((round(query[start].t_ms / 1000, 1), round(end_t / 1000, 1)))
            start = None
    return out


def verdict(pct: float, modified: list) -> str:
    if pct < 30:
        return "NO MATCH"
    if pct >= 90 and not modified:
        return "AUTHENTIC"
    return "MODIFIED"


def match(query: list[Sample], stored: list[Sample], threshold: int) -> dict:
    """Full comparison of one video against one trip."""
    if not query or not stored:
        return {"verdict": "NO MATCH", "matched_pct": 0.0, "mean_distance": None, "position_s": None,
                "modified_sections": [], "samples": len(query), "matched_samples": 0, "distances": []}
    offset, mean = best_offset(query, stored)
    d = distances(query, stored, offset)
    matched = [x is not None and x <= threshold for x in d]
    pct = round(100 * sum(matched) / len(query), 1)
    modified = sections(query, matched)
    return {
        "verdict": verdict(pct, modified),
        "matched_pct": pct,
        "mean_distance": round(mean, 2),
        "position_s": round(offset / 1000, 1),   # where the video's t=0 is in the trip
        "modified_sections": [{"from_s": a, "to_s": b} for a, b in modified],
        "samples": len(query),
        "matched_samples": sum(matched),
        "distances": d,
    }
