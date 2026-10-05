# CLAUDE.md — Dashcam Video Integrity Project

You are the main developer. The owner reviews block by block. Read this file and `PLAN.md` at the
start of every session and continue from the first unfinished block.

## 0. Priorities (read first)
- **Deadline today. Solo developer. Goal: simple and functional, not precise or pretty.**
- Plain, minimal UI (simple HTML + a little CSS). No frameworks, no design work.
- Choose the simplest correct solution. No over-engineering. If something gets complicated,
  simplify and write the limitation in the docs.
- Runs **locally**: encoder on `http://localhost:5173` using the **laptop webcam** (localhost is a
  secure context, so no HTTPS needed) or a **video file** as source. Deploying to Vercel for a phone
  is optional at the very end.
- Work autonomously inside a block; stop only when the owner must act (Supabase keys, SQL, testing).
- All code, UI text, docs and reports in **English**.

## 1. What we are building
```
[Encoder web app]  --hashes-->  [Supabase Postgres]  <--reads--  [Decoder: Python FastAPI + 1 HTML page]
 camera/file -> canvas frames      trips, segments,                upload video -> hashes -> slide over
 -> 10 s video segments            fingerprints                    stored hashes -> report
 SHA-256 per segment + pHash/dHash  (duplicates ignored)
 offline queue + retry + cleanup
```
- **Encoder (20 pts)**: frame acquisition from camera, video composed from those frames, hash
  generation, live transmission to Supabase, network-loss handling (local queue + retry + no
  duplicates), deletion of expired data.
- **Decoder (20 pts)**: verify a submitted video against the stored hashes: match or not, position in
  the trip, % matched, modified sections, processing time. Exact check via SHA-256.
- **Evaluation**: test videos with all transformations from the assignment, comparison of distance
  metrics (Hamming/normalized Hamming for aHash/dHash/pHash/wHash, ssdeep, TLSH, L1/L2/cosine) and a
  threshold for each. Done offline in Python.

## 2. Design decisions
1. **Two hash types**: SHA-256 per video segment (exact integrity, breaks on any change) and
   perceptual hashes per sampled frame (survive re-encoding, brightness, noise...).
2. The encoder sends **pHash and dHash** only (2 samples per second). The full metric comparison
   (aHash, wHash, fuzzy, vectors) is done offline in `eval/` with Python on video files.
3. Video composition: draw camera frames on a `<canvas>` → `canvas.captureStream()` →
   `MediaRecorder`, restarted every 10 s so each segment is a standalone file (SHA-256 per segment).
   Hashes are computed from the same canvas.
4. Same pHash/dHash algorithm in JS and Python (simple custom implementation, see PLAN Block 1).
   They do not need to be bit-identical: a test checks they differ by only a few bits.
5. **Idempotency**: primary key `(trip_id, sample_idx)` + upsert with `ignoreDuplicates` → resending
   is harmless; order does not matter. Queue in IndexedDB, items deleted only after server OK.
6. **Matching** (simple): sliding window — try every offset of the query hash sequence over the
   stored sequence, take the offset with the lowest mean Hamming distance = temporal position. Then
   each sample is "matched" if its distance ≤ threshold; consecutive unmatched samples = modified section.
7. **No user auth** (simplicity): driver ID typed in the UI, like the professor's example. Supabase
   RLS allows anon `insert` + `select` only, no `update`/`delete` (append-only record). Documented
   as a limitation.
8. Thresholds come from `eval/` results and are stored in `decoder/thresholds.json`.

## 3. Layout
```
/encoder   Vite + TypeScript, plain HTML (index.html), Vitest
/decoder   FastAPI app (main.py, fingerprint.py, matching.py, static/index.html), pytest
/supabase  schema.sql (pasted by the owner in the SQL Editor)
/eval      make_variants.py, metric_study.py, video_eval.py, data/ (gitignored), results/
/docs      encoder-report.md, decoder-report.md, demo-encoder.md, demo-decoder.md
```

## 4. Stack
- Node LTS, Vite, TypeScript, `@supabase/supabase-js`, `idb`, Vitest.
- Python ≥ 3.11 venv: fastapi, uvicorn, python-multipart, supabase, python-dotenv, numpy,
  opencv-python-headless, imagehash, Pillow, PyWavelets, ppdeep, py-tlsh, pandas, matplotlib,
  scikit-learn, pytest. System `ffmpeg`.

## 5. Commands (keep updated)
```
cd encoder && npm install && cp .env.example .env && npm run dev   # http://localhost:5173
cd encoder && npm test                            # Vitest (hash parity, offline queue)
cd encoder && SUPABASE_IT=1 npm test              # + integration test against the real Supabase
python3 -m venv .venv  (Windows: .venv\Scripts\activate | mac/linux: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn decoder.main:app --reload                 # http://localhost:8000  (GET /health)
python -m pytest                                  # decoder tests (run from repo root)
python -m decoder.tests.make_hash_fixtures        # regenerate hash parity fixtures
# Supabase: paste supabase/schema.sql in the SQL Editor (safe to re-run)
python eval/make_variants.py eval/data/original.mp4
python eval/metric_study.py && python eval/video_eval.py
```

## 6. Rules
- One block at a time; run tests; tick `PLAN.md`; update §5; commit + push; short summary of what
  the owner must check.
- Secrets only in `.env` files (gitignored); keep `.env.example`.
- Keep code short and readable — the owner must explain it orally. Comment the "why".
- Numbers in reports come from the eval scripts, never invented.
