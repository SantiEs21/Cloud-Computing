# Demo video — Decoder (~3 min)

Before recording: `uvicorn decoder.main:app`, open http://localhost:8000 and press **Decoder** at the top
(or go to http://localhost:8000/decoder/). Have ready:
a segment downloaded from the encoder, `eval/data/variants/` (brightness_0_2, partial_replace,
trim_start, other_trip) and `eval/results/`.

**Trip selector:** "Auto" only in step 2. For steps 3–6 select trip **`a2280b49`** (trip A — match
the ID prefix; several trips show driver-42). With Auto, `other_trip.mp4` would correctly match its own
trip B instead of showing NO MATCH.

**Server purge:** the encoder purges server rows older than 24 h every minute. Record this demo the same
day as trip A (5 Oct), or raise "Keep server data (h)" in the encoder before opening it later.

| # | Time | Show | Say |
|---|---|---|---|
| 1 | 0:00–0:15 | Decoder page | "The decoder checks a video against the hashes stored by the encoder." |
| 2 | 0:15–0:45 | Trip = Auto, upload the **downloaded segment** (download it within 10 min of recording), Verify → AUTHENTIC, "Exact SHA-256 match: YES" | "The file is byte-identical to a recorded segment, so the SHA-256 matches. Perceptual check: 100 % matched, position in the trip, processing time." |
| 3 | 0:45–1:10 | Trip `a2280b49`, upload `brightness_0_2.mp4` → AUTHENTIC, no exact match | "Re-encoded and brighter: SHA-256 breaks, but pHash still matches — mean distance about 3 bits, threshold 16." |
| 4 | 1:10–1:30 | `trim_start.mp4` → AUTHENTIC, position 10.1 s | "A cut piece is found at its position in the trip thanks to the sliding window." |
| 5 | 1:30–2:00 | `partial_replace.mp4` → MODIFIED, red block in the bar, section 42.0–47.5 s | "5 seconds were replaced with another video: detected and located." |
| 6 | 2:00–2:15 | `other_trip.mp4` → NO MATCH | "A different trip does not match." |
| 7 | 2:15–2:45 | `eval/results/thresholds.csv` / a histogram, and `video_eval.md` summary | "We compared aHash, dHash, pHash, wHash, ssdeep, TLSH, L1, L2 and cosine. pHash at 16 bits: 98.9 % accuracy, 0 false positives. On 21 variants: 20 correct, 0 false matches, 5/5 modifications." |
| 8 | 2:45–3:00 | Limitations list in `docs/decoder-report.md` | "Limitations: crop, one global offset for cuts and speed changes, no authentication." |
