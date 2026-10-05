# PLAN.md — Simple one-day plan

`[ ]` todo · `[x]` done · 👤 owner action. Each block leaves the project submittable. Keep it simple.

---

## Block 1 — Setup + hashing (~45 min)
- [x] Layout from CLAUDE.md §3, `.gitignore` (node_modules, .venv, .env*, eval/data, dist,
      __pycache__), root `README.md`, root `requirements.txt`.
- [x] `encoder/`: Vite vanilla-ts, Vitest, `.env.example` (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`).
- [x] `decoder/`: FastAPI with `/health`, `.env.example` (`SUPABASE_URL`, `SUPABASE_ANON_KEY`).
- [x] Hash algorithm, same in `encoder/src/hash.ts` and `decoder/fingerprint.py`:
      frame → grayscale (`0.299R+0.587G+0.114B`) → resize to 32×32 (encoder: draw on a 32×32 canvas;
      decoder: `cv2.resize(INTER_AREA)`) →
      - **pHash**: 2-D DCT, top-left 8×8, bit = value > median → 16 hex chars
      - **dHash**: resize 9×8, bit = right pixel > left pixel → 16 hex chars
      Plus `hamming(a, b)` helper.
- [x] Python also has aHash and wHash (use `imagehash` library is fine here) for the evaluation.
- [x] Test: same image hashed in JS and Python → Hamming ≤ 4 bits (export 3 test PNGs + their
      Python hashes to a JSON used by the Vitest test).
- Note: the encoder does NOT resize on a 32×32 canvas; it takes `getImageData` of the capture canvas
  and resizes in JS (area average, like `INTER_AREA`), so Vitest tests the exact browser code.
  dHash uses `right − left > 1e-3` so exact ties (flat areas) are always 0 in both languages.
  Fixtures: `python -m decoder.tests.make_hash_fixtures` → `encoder/test/fixtures/`.

## Block 2 — Supabase + Encoder (~2 h)
### 2.1 Supabase (👤 owner pastes `supabase/schema.sql` in SQL Editor)
```sql
trips(id uuid pk, driver_id text, started_at timestamptz, created_at timestamptz default now())
segments(trip_id uuid, seq int, t_start_ms int, duration_ms int, sha256 text, size_bytes int,
         created_at timestamptz default now(), primary key(trip_id, seq))
fingerprints(trip_id uuid, sample_idx int, t_ms int, phash text, dhash text,
         created_at timestamptz default now(), primary key(trip_id, sample_idx))
```
- [x] RLS on: anon may `insert` and `select`, nothing else. (verified by `SUPABASE_IT=1 npm test`)
- [x] Function `purge_expired(hours int)` deleting rows older than N hours (security definer),
      callable via RPC. Optional `pg_cron` job every 10 min with a comment on how to enable it.

### 2.2 Encoder page (one simple page)
- [x] Inputs: Driver ID, Source (Webcam / Video file). Buttons: Start, Stop, "Simulate offline"
      checkbox. Live preview.
- [x] Status list: frames captured, hashes generated, sent, pending (offline), network state,
      recording time, last upload latency.
- [x] Capture: draw source on a canvas at 15 fps → `canvas.captureStream(15)` → `MediaRecorder`
      (`video/webm` in Chrome; mp4 if supported). Restart every 10 s → segment blob →
      SHA-256 (`crypto.subtle`) → segment row.
- [x] Every 500 ms: hash the canvas (pHash + dHash) → fingerprint row with `sample_idx`, `t_ms`
      (in file mode `t_ms = video.currentTime*1000`).
- [x] Queue: every row is saved in IndexedDB (`idb`) first, then sent in batches with
      `upsert(..., {ignoreDuplicates: true})`; removed from the queue only after success.
      Retry every 3 s while items are pending and on the `online` event. "Simulate offline"
      makes the sender skip sending (or throw) so the queue grows.
- [x] Cleanup: segments stored in IndexedDB; delete those older than 10 min (configurable) every
      minute. List of local segments with a **Download** link (needed to test the decoder).
- [x] Vitest: queue keeps items while offline, empties after reconnect, sending the same batch
      twice produces no error.

- Limitations (for the reports): use **Chrome** (webm; Safari records MP4); keep the encoder tab
  **visible** while recording (background tabs throttle timers to ~1 s → fewer frames and samples);
  `purge_expired` has a 1 h minimum so the public key cannot wipe fresh data, but anyone with the
  key can purge data older than that (no auth).

👤 Check: record 1 min with webcam, tick "Simulate offline" 20 s (or DevTools → Network → Offline),
see pending grow then go to 0; Supabase table shows no gaps in `sample_idx`.

## Block 3 — Decoder (~1.5 h)
- [x] `decoder/matching.py`: (verified on a real Chrome webm segment: exact SHA match, AUTHENTIC,
      position 0.0 s, mean 3.0 bits; file-mode trip `a2280b49` vs tripA.mp4: AUTHENTIC 100 %)
  1. Read the uploaded video with OpenCV, take one frame every 500 ms (by timestamp), compute pHash.
  2. Load the trip's fingerprints from Supabase ordered by `t_ms`.
  3. Sliding window: for each offset, mean Hamming distance query vs stored → best offset.
  4. Per sample: matched if distance ≤ threshold (default 10 bits until eval gives one).
  5. Consecutive unmatched (≥ 2) → "modified section from X s to Y s".
  6. Verdict: `AUTHENTIC` (≥ 90 % matched), `MODIFIED` (30–90 % or modified sections),
     `NO MATCH` (< 30 %).
- [x] Exact check: SHA-256 of uploaded file equals a stored segment → "bit-exact original segment N".
- [x] `POST /api/verify` (trip_id or driver_id + video) → JSON: verdict, score, % matched, position
      in trip (s), modified sections, number of samples, processing time. `GET /api/trips`.
      `POST /api/purge` (calls `purge_expired`).
- [x] `static/index.html`: select trip, upload video, Verify button, result table, simple colored bar
      (green matched / red unmatched), Purge button.
- [x] pytest on matching with fake hash lists (shifted, part replaced, other trip).

- Note: matching aligns by `t_ms` (nearest stored sample in time), not by index, because browser
  timers jitter (seen in a real trip: 197–1007 ms spacing). No `trip_id` → all trips are compared.

- Limitation: two trips of the same static scene (webcam on a desk) look the same to perceptual
  hashes → negative checks must use visually different videos.

👤 Check: download a segment from the encoder → AUTHENTIC + bit-exact; segment of another trip → NO MATCH.

## Block 4 — Evaluation (~1.5 h)
👤 Data: record 2 trips with the encoder (file mode with 2 different dashcam videos is easiest),
put the videos in `eval/data/` (`tripA.mp4`, `tripB.mp4`) and give the trip IDs.
- [x] `make_variants.py` (ffmpeg, one variant each): trim start, trim end, extract middle, shift
      (3 s black at start), speed ×1.05, FPS 10, delete 1 s of frames, duplicate 1 s, H.265, low
      bitrate (300k), resolution 640×360, high compression (CRF 40), brightness +0.2, contrast 1.5,
      salt-and-pepper 5 % (OpenCV), Gaussian noise, logo overlay, crop 80 %, other trip,
      partial replacement (A with 5 s of B).
- [x] `metric_study.py`: original vs each variant frame by frame (same timestamps) = positive pairs;
      trip A vs trip B = negative pairs. Distances: aHash/dHash/pHash/wHash with Hamming and
      normalized Hamming; ssdeep and TLSH on JPEG bytes of each frame; L1/L2/cosine on a 16×16
      grayscale vector. For each metric: mean distance per variant, threshold = best accuracy
      between positives and negatives, plus a histogram plot. Save `results/metrics.csv`,
      `results/thresholds.csv`, plots; write the pHash threshold to `decoder/thresholds.json`.
- [x] `video_eval.py`: run the decoder matching on every variant against trip A → table: expected,
      verdict, correct?, % matched, position found, modified sections, time. Count true matches,
      false matches, missed matches, detected modifications → `results/video_eval.csv` + `.md`.
- [x] 👤 Network tests table (real offline rows + duplicate sends filled; other rows optional) (manual, filled in by the owner with values seen in the app): offline 30 s,
      intermittent, server unreachable (wrong URL in `.env`), duplicate sends. Template in
      `results/network_tests.md`.
- Results: trip A = `a2280b49` (tripA.mp4, 84 s), trip B = `e2b53bdc` (tripB.mp4). Variants are made
  from a 720p copy (4K too slow). pHash threshold = 16 bits. Video eval: 20/21 correct (crop 80 % missed).

## Block 5 — Reports + demo (~1 h + 👤 recording)
- [x] `docs/encoder-report.md` & `docs/decoder-report.md`: 1) install & run step by step
      (Windows + macOS), 2) how it works + why each choice (short), 3) results tables from
      `eval/results` + limitations (speed changes, crop, big logos, no auth, browser must stay open).
- [x] `docs/demo-encoder.md` (~2–3 min) and `docs/demo-decoder.md` (~3 min): shot list.
- [ ] Optional: deploy encoder to Vercel to show it opens on a phone.

## Block 6 — One server, one port
- [x] FastAPI serves the built encoder at `/` and the decoder at `/decoder/`; Encoder | Decoder buttons
      on both pages. `cd encoder && npm run build` once, then only `uvicorn decoder.main:app`.
- [x] Checked end to end in Chrome on :8000 (fake camera + file mode): record, simulate offline,
      switch page, verify segment → AUTHENTIC, exact SHA-256 match.

---
**If short on time, cut:** pg_cron job → Gaussian noise / contrast / FPS variants → histogram plots →
Vercel. **Never cut:** offline queue, decoder verdict, metric/threshold table, reports.
