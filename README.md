# Dashcam Video Integrity

Encoder (browser) records dashcam video from the webcam or a video file, cuts it in 10 s segments and
sends SHA-256 + perceptual hashes (pHash/dHash) to Supabase. Decoder (FastAPI) verifies an uploaded
video against the stored hashes. `eval/` compares distance metrics and picks thresholds.

See `CLAUDE.md` (design) and `PLAN.md` (progress).

## Quick start (one server, one port)
```
cp encoder/.env.example encoder/.env && cp decoder/.env.example decoder/.env   # fill in Supabase URL + key
cd encoder && npm install && npm run build && cd ..                            # build the encoder page
python3 -m venv .venv && source .venv/bin/activate                             # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn decoder.main:app                                                       # http://localhost:8000
```
`/` = encoder, `/decoder/` = decoder (buttons at the top of both pages), `/api/...` = decoder API.
Tests: `cd encoder && npm test` and `python -m pytest`.

## Layout
- `encoder/` Vite + TypeScript, `src/hash.ts` = pHash/dHash (same algorithm as `decoder/fingerprint.py`)
- `decoder/` FastAPI, `fingerprint.py`, tests in `decoder/tests/`
- `supabase/` SQL schema · `eval/` offline evaluation · `docs/` reports
