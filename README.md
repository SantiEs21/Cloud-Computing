# Dashcam Video Integrity

Checks that dashcam video has not been tampered with.

- **Encoder** (web page): records video from the webcam or a video file, cuts it into 10 s segments,
  computes a SHA-256 per segment and perceptual hashes (pHash + dHash) every 0.5 s, and sends the hashes
  live to Supabase. Works offline: rows are queued in the browser and uploaded later, without losses or
  duplicates. Old data is deleted automatically.
- **Decoder** (web page + Python API): verifies a video against the stored hashes — match or not, which
  trip, position in the trip, % matched, modified sections, bit-exact segment check, processing time.

Both pages run on **one local server, one port**: http://localhost:8000 (buttons at the top switch
between Encoder and Decoder).

The full report (design, results, limitations) is in **`docs/report.md`**.

## Run it

Requirements: Python ≥ 3.11, Node.js LTS, Google Chrome. Supabase connection:
`encoder/.env` and `decoder/.env` (if missing, copy the `.env.example` files, create a Supabase project
and run `supabase/schema.sql` in its SQL Editor).

**macOS / Linux**
```bash
cd encoder && npm install && npm run build && cd ..   # builds the encoder page (once)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn decoder.main:app                              # open http://localhost:8000
```

**Windows (PowerShell)**
```powershell
cd encoder; npm install; npm run build; cd ..
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn decoder.main:app                              # open http://localhost:8000
```

## Tests
```bash
cd encoder && npm test                 # hash parity JS vs Python, offline queue
cd encoder && SUPABASE_IT=1 npm test   # + integration tests against Supabase (duplicates, append-only, purge)
python -m pytest                       # hashing, matching, pages and API
```

## Evaluation (reproduce the results)
The test videos are not included (too large). With two dashcam videos recorded through the encoder in
file mode (`eval/data/tripA.mp4`, `eval/data/tripB.mp4`) and `ffmpeg` installed:
```bash
python eval/make_variants.py eval/data/tripA.mp4 eval/data/tripB.mp4   # 21 variants (~12 min)
python -m eval.metric_study                       # metric comparison + thresholds -> decoder/thresholds.json
python -m eval.video_eval <trip A id>             # decoder on every variant
python -m eval.plots <online trip id> <offline trip id>   # figures for the report
python docs/build_pdf.py                          # docs/report.md -> docs/report.pdf (needs Chrome)
```
Results are already in `eval/results/` (CSV, Markdown tables and figures).

## Project structure
```
encoder/    Vite + TypeScript web page
  src/hash.ts       pHash / dHash (same algorithm as decoder/fingerprint.py)
  src/recorder.ts   canvas -> 10 s MediaRecorder segments + SHA-256, hash every 0.5 s
  src/queue.ts      offline queue (IndexedDB) + retry, idempotent upload
  src/db.ts         local storage of the queue and segments, expiry cleanup
  src/supabase.ts   upsert ignoring duplicates, purge RPC
  test/             Vitest tests (+ fixtures for the JS/Python hash parity test)
decoder/    FastAPI server: serves both pages and the API
  main.py           routes: /, /decoder/, /api/verify, /api/trips, /api/purge
  matching.py       video sampling + sliding-window matching + verdict
  fingerprint.py    pHash / dHash (+ aHash / wHash for the evaluation)
  static/index.html decoder page
  thresholds.json   pHash threshold from the evaluation
  tests/            pytest tests
supabase/schema.sql tables, append-only RLS, purge_expired()
eval/       offline evaluation scripts and results/
docs/       report.md (report), build_pdf.py (report -> PDF)
```
