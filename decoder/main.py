"""Decoder API. Run from the repo root: uvicorn decoder.main:app --reload"""
from fastapi import FastAPI

app = FastAPI(title="Dashcam decoder")


@app.get("/health")
def health():
    return {"status": "ok"}
