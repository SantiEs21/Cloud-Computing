"""Writes 3 test PNGs + their Python hashes to encoder/test/fixtures/ for the JS/Python parity test.

Run: python -m decoder.tests.make_hash_fixtures   (outputs are committed, so npm test needs no Python)
"""
import json
from pathlib import Path

import cv2
import numpy as np

from decoder.fingerprint import dhash, gray32, phash

OUT = Path(__file__).resolve().parents[2] / "encoder" / "test" / "fixtures"


def make_images():
    rng = np.random.default_rng(42)
    h, w = 240, 320
    # Textured images (blurred noise + shapes): flat areas would make dHash bits ties.
    noise = cv2.GaussianBlur(rng.integers(0, 256, (h, w, 3), dtype=np.uint8), (0, 0), 6)
    img1 = noise.copy()
    cv2.circle(img1, (100, 120), 60, (30, 200, 240), -1)
    cv2.rectangle(img1, (190, 40), (300, 200), (200, 50, 20), -1)

    yy, xx = np.mgrid[0:h, 0:w]
    waves = (127 + 100 * np.sin(xx / 17.0) * np.cos(yy / 23.0)).astype(np.uint8)
    img2 = cv2.merge([waves, np.roll(waves, 40, axis=1), noise[:, :, 0]])

    img3 = cv2.GaussianBlur(rng.integers(0, 256, (h, w, 3), dtype=np.uint8), (0, 0), 3)
    cv2.line(img3, (0, 0), (w, h), (255, 255, 255), 12)
    return [img1, img2, img3]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fixtures = []
    for i, img in enumerate(make_images(), 1):
        name = f"img{i}.png"
        cv2.imwrite(str(OUT / name), img)
        img = cv2.imread(str(OUT / name))  # hash what is on disk, exactly what JS will read
        fixtures.append({
            "file": name,
            "phash": phash(img),
            "dhash": dhash(img),
            "gray32": np.round(gray32(img), 2).flatten().tolist(),  # debug aid if parity fails
        })
    (OUT / "hashes.json").write_text(json.dumps(fixtures))
    print(f"wrote {len(fixtures)} fixtures to {OUT}")


if __name__ == "__main__":
    main()
