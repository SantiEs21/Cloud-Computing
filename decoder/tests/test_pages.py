# One server serves both pages and the API (see decoder/main.py).
from fastapi.testclient import TestClient

from decoder.main import app

client = TestClient(app)


def test_encoder_page_at_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "Dashcam Encoder" in r.text or "Encoder not built" in r.text


def test_decoder_page():
    r = client.get("/decoder/")
    assert r.status_code == 200
    assert "Dashcam Decoder" in r.text
    assert client.get("/decoder", follow_redirects=False).status_code in (307, 308)  # -> /decoder/


def test_api_still_wins_over_pages():
    assert client.get("/health").json() == {"status": "ok"}
    assert isinstance(client.get("/api/trips").json(), list)
