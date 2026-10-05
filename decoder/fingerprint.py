"""Perceptual hashes of a video frame.

pHash and dHash use the SAME algorithm as encoder/src/hash.ts so hashes made in the browser can be
compared with hashes made here from a video file. aHash and wHash (imagehash library) are only used
by the offline evaluation in eval/.
"""
import cv2
import imagehash
import numpy as np
from PIL import Image


EPS = 1e-3


def gray32(frame_bgr: np.ndarray) -> np.ndarray:
    """BGR frame -> float grayscale -> 32x32 (area average). Float math to match the JS code."""
    f = frame_bgr.astype(np.float32)
    gray = 0.299 * f[:, :, 2] + 0.587 * f[:, :, 1] + 0.114 * f[:, :, 0]  # OpenCV is BGR
    return cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)


def bits_to_hex(bits) -> str:
    """64 booleans (row-major, MSB first) -> 16 hex chars."""
    out = ""
    for i in range(0, len(bits), 4):
        nibble = 0
        for b in bits[i:i + 4]:
            nibble = (nibble << 1) | int(bool(b))
        out += format(nibble, "x")
    return out


def phash(frame_bgr: np.ndarray) -> str:
    # 2-D DCT keeps the low frequencies (overall structure) in the top-left corner;
    # comparing them to their median makes the hash robust to brightness/compression.
    dct = cv2.dct(gray32(frame_bgr))  # orthonormal DCT-II, same as the JS implementation
    low = dct[:8, :8].flatten()
    return bits_to_hex(low > np.median(low))


def dhash(frame_bgr: np.ndarray) -> str:
    # 9x8 so each row gives 8 left/right comparisons -> 64 bits (encodes gradients).
    small = cv2.resize(gray32(frame_bgr), (9, 8), interpolation=cv2.INTER_AREA)  # (width, height)
    # EPS: flat areas (e.g. white sky) give exact ties; float rounding differences between
    # JS and Python would flip those bits randomly, so a tie always counts as 0.
    return bits_to_hex((small[:, 1:] - small[:, :-1] > EPS).flatten())


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


# --- extra hashes for the evaluation only (library implementation is fine here) ---
def _pil(frame_bgr: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))


def ahash(frame_bgr: np.ndarray) -> str:
    return str(imagehash.average_hash(_pil(frame_bgr)))


def whash(frame_bgr: np.ndarray) -> str:
    return str(imagehash.whash(_pil(frame_bgr)))
