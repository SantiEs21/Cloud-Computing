# Demo video — Encoder (~2–3 min)

Before recording: `uvicorn decoder.main:app` (repo root), Chrome at http://localhost:8000, Supabase dashboard
open in a **separate window** (Table Editor → `fingerprints`). Keep the encoder tab visible.

| # | Time | Show | Say |
|---|---|---|---|
| 1 | 0:00–0:15 | The encoder page; point at the **Encoder / Decoder** buttons | "One local server: this page records, the Decoder page verifies. The encoder records dashcam video, hashes it and sends the hashes to Supabase." |
| 2 | 0:15–0:45 | Driver ID, Webcam, **Start**. Preview moving; Frames / Hashes / Rows sent increasing | "Frames are drawn on a canvas at 15 fps. The canvas is recorded in 10-second segments, each with a SHA-256. Every 0.5 s we compute a pHash and a dHash." |
| 3 | 0:45–1:00 | Supabase window: new rows in `fingerprints` and `segments` | "Hashes arrive live, every 3 seconds." |
| 4 | 1:00–1:40 | Tick **Simulate offline** (or turn Wi-Fi off) for ~20 s: Pending grows, Network = offline. Untick: Pending goes to 0 | "Without network everything is queued in IndexedDB. Rows are deleted from the queue only after the server confirms, so nothing is lost." |
| 5 | 1:40–2:00 | Supabase: `sample_idx` of the trip has no gaps | "No gaps. Re-sending is harmless: the primary key plus upsert-ignore-duplicates prevents duplicates." |
| 6 | 2:00–2:20 | **Stop**. Local segments list → **Download** one | "Segments stay locally for 10 minutes; this file is what we give to the decoder." |
| 7 | 2:20–2:40 | Status row "Last cleanup" (wait 1 min or show the settings) | "Every minute old local segments are deleted and the server purges rows older than 24 hours." |
| 8 | 2:40–2:50 | Optional: switch Source to Video file, Start with a dashcam video | "The same pipeline works with a video file as source." |
