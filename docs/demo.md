# Demo video — Dashcam Video Integrity (~5 min)

**Before recording**
- Start the server from the repo root: `source .venv/bin/activate && uvicorn decoder.main:app`, open
  http://localhost:8000 in Chrome. Keep this tab visible while recording.
- Supabase dashboard open in a **separate window** (Table Editor → `fingerprints`).
- Files ready in `eval/data/variants/`: `brightness_0_2.mp4`, `trim_start.mp4`, `partial_replace.mp4`,
  `other_trip.mp4`; and `eval/results/` (a histogram + `video_eval.md`).
- **Trip A for steps 10–13:** the variants in `eval/data/variants/` are made from trip A, so record
  trip A once before the demo: encoder → Video file → `eval/data/variants/base_A.mp4` → Start, keep the
  tab visible and let it finish by itself (~84 s, 168 samples). Note its Trip ID.
- **Trip selector in the decoder:** "Auto" only for the segment you just recorded (step 9). For steps
  10–13 select **trip A** (each option ends with the first 8 characters of the trip ID). With Auto, `other_trip.mp4` could match
  another trip instead of showing NO MATCH.
- **Server purge:** the encoder purges server rows older than "Keep server data (h)" every minute.
  Record the demo within 24 h of recording trip A (or raise that value).

## Part 1 — Encoder (`/`)

| # | Time | Show | Say |
|---|---|---|---|
| 1 | 0:00–0:20 | The page; point at the **Encoder / Decoder** buttons | "One local server, one port. This page records and hashes dashcam video; the Decoder page verifies it." |
| 2 | 0:20–0:50 | Driver ID, Webcam, **Start**. Preview moving; Frames / Hashes / Rows sent increasing | "Frames are drawn on a canvas at 15 fps. The canvas is recorded in 10-second segments, each with a SHA-256. Every 0.5 s we compute a pHash and a dHash." |
| 3 | 0:50–1:05 | Supabase window: new rows in `fingerprints` and `segments` | "Hashes arrive live, every 3 seconds." |
| 4 | 1:05–1:45 | Tick **Simulate offline** (or turn Wi-Fi off) for ~20 s: Pending grows, Network = offline. Untick: Pending goes to 0 | "Without network everything is queued in IndexedDB. Rows leave the queue only after the server confirms, so nothing is lost." |
| 5 | 1:45–2:00 | Supabase: `sample_idx` of the trip has no gaps | "No gaps. Re-sending is harmless: primary key plus upsert-ignore-duplicates prevents duplicates." |
| 6 | 2:00–2:15 | Status row "Last cleanup" | "Every minute old local segments are deleted and the server purges rows older than 24 hours." |
| 7 | 2:15–2:30 | **Stop**. Local segments list → **Download** segment 0 | "The video stays on the device; only hashes go to the server. This file is what we verify next." |

## Part 2 — Decoder (`/decoder/`)

| # | Time | Show | Say |
|---|---|---|---|
| 8 | 2:30–2:40 | Click **Decoder** at the top | "Same server, decoder page." |
| 9 | 2:40–3:05 | Trip = **Auto**, upload the segment just downloaded → AUTHENTIC, "Exact SHA-256 match: YES" | "The file is byte-identical to a recorded segment, so the SHA-256 matches. Perceptual check: matched %, position in the trip, processing time." |
| 10 | 3:05–3:30 | Trip A, `brightness_0_2.mp4` → AUTHENTIC, no exact match | "Re-encoded and brighter: SHA-256 breaks, but pHash still matches — about 3 bits, threshold 16." |
| 11 | 3:30–3:50 | `trim_start.mp4` → AUTHENTIC, position 10.1 s | "A cut piece is found at its position in the trip thanks to the sliding window." |
| 12 | 3:50–4:15 | `partial_replace.mp4` → MODIFIED, red block in the bar, section 42.0–47.5 s | "5 seconds were replaced with another video: detected and located." |
| 13 | 4:15–4:30 | `other_trip.mp4` → NO MATCH | "A different trip does not match." |
| 14 | 4:30–4:50 | A histogram and the `video_eval.md` summary | "We compared aHash, dHash, pHash, wHash, ssdeep, TLSH, L1, L2 and cosine. pHash at 16 bits: 98.9 % accuracy, 0 false positives. On 21 variants: 20 correct, 0 false matches, 5/5 modifications." |
| 15 | 4:50–5:00 | Limitations in `docs/report.md` | "Limitations: crop, one global offset for cuts and speed changes, no authentication." |
