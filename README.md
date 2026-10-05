# Dashcam Video Integrity

Encoder (browser) records dashcam video from the webcam or a video file, cuts it in 10 s segments and
sends SHA-256 + perceptual hashes (pHash/dHash) to Supabase. Decoder (FastAPI) verifies an uploaded
video against the stored hashes. `eval/` compares distance metrics and picks thresholds.

See `CLAUDE.md` (design) and `PLAN.md` (progress).

## Quick start
```
# encoder  -> http://localhost:5173
cd encoder && npm install && cp .env.example .env && npm run dev
cd encoder && npm test

# decoder  -> http://localhost:8000
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp decoder/.env.example decoder/.env
uvicorn decoder.main:app --reload
python -m pytest
```

## Layout
- `encoder/` Vite + TypeScript, `src/hash.ts` = pHash/dHash (same algorithm as `decoder/fingerprint.py`)
- `decoder/` FastAPI, `fingerprint.py`, tests in `decoder/tests/`
- `supabase/` SQL schema · `eval/` offline evaluation · `docs/` reports
