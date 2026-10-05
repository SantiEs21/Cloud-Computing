import cv2
import numpy as np
from fastapi.testclient import TestClient

from decoder.fingerprint import ahash, dhash, hamming, phash, whash
from decoder.main import app
from decoder.tests.make_hash_fixtures import make_images


def test_hash_format_and_identity():
    img = make_images()[0]
    for h in (phash, dhash, ahash, whash):
        assert len(h(img)) == 16
        assert hamming(h(img), h(img)) == 0


def test_robust_to_small_changes_but_not_other_images():
    a, b, _ = make_images()
    brighter = cv2.convertScaleAbs(a, alpha=1.0, beta=20)
    jpeg = cv2.imdecode(cv2.imencode(".jpg", a, [cv2.IMWRITE_JPEG_QUALITY, 30])[1], cv2.IMREAD_COLOR)
    for h in (phash, dhash):
        assert hamming(h(a), h(brighter)) <= 6
        assert hamming(h(a), h(jpeg)) <= 6
        assert hamming(h(a), h(b)) > 15


def test_hamming():
    assert hamming("0000000000000000", "ffffffffffffffff") == 64
    assert hamming("000000000000000f", "0000000000000001") == 3


def test_health():
    assert TestClient(app).get("/health").json() == {"status": "ok"}
