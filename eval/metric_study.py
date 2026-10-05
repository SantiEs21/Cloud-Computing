"""Comparison of distance metrics on frame pairs.

Positive pairs: frame of the original trip A vs the frame at the SAME timestamp in a variant that keeps
the content (re-encoding, brightness, noise, ...). Negative pairs: frame of trip A vs frame of trip B.
For each metric: mean distance per variant, and the threshold that best separates positives from
negatives (best accuracy). Writes results/metrics.csv, results/thresholds.csv, histogram plots and
the pHash threshold to decoder/thresholds.json.

Usage: python eval/metric_study.py   (after make_variants.py)
"""
import json
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ppdeep
import tlsh

from decoder.fingerprint import ahash, dhash, hamming, phash, whash

ROOT = Path(__file__).resolve().parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
STEP_S = 1.0  # one pair per second of video is plenty for statistics

# Variants whose frames are the same content at the same timestamp (temporal edits are excluded:
# their frames are not aligned in time, they are evaluated by video_eval.py instead).
ALIGNED = ["original", "fps_10", "h265", "bitrate_300k", "res_640x360", "crf_40", "brightness_0_2",
           "contrast_1_5", "salt_pepper_5", "gaussian_noise", "logo", "crop_80"]


def frames(path: Path, step_s=STEP_S, limit=None) -> dict[int, np.ndarray]:
    """Frames every step_s seconds, keyed by time in ms (rounded to the step)."""
    cap = cv2.VideoCapture(str(path))
    out, next_t = {}, 0.0
    while True:
        ok, f = cap.read()
        if not ok or (limit and len(out) >= limit):
            break
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if t + 1e-6 >= next_t:
            out[int(round(next_t * 1000))] = f
            next_t += step_s
    cap.release()
    return out


# ---- features + distances -------------------------------------------------------------------
def vec16(f):
    """16x16 grayscale vector for L1/L2/cosine."""
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    return cv2.resize(g, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32).flatten() / 255


def jpeg(f):
    small = cv2.resize(f, (320, 180), interpolation=cv2.INTER_AREA)
    return cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 80])[1].tobytes()


def features(f):
    j = jpeg(f)
    return {"ahash": ahash(f), "dhash": dhash(f), "phash": phash(f), "whash": whash(f),
            "ssdeep": ppdeep.hash(j), "tlsh": tlsh.hash(j), "vec": vec16(f)}


def distances(a, b) -> dict[str, float]:
    d = {}
    for h in ("ahash", "dhash", "phash", "whash"):
        d[f"{h}_hamming"] = hamming(a[h], b[h])
        d[f"{h}_norm"] = hamming(a[h], b[h]) / 64
    d["ssdeep"] = 100 - ppdeep.compare(a["ssdeep"], b["ssdeep"])  # similarity 0..100 -> distance
    d["tlsh"] = tlsh.diff(a["tlsh"], b["tlsh"]) if a["tlsh"] != "TNULL" and b["tlsh"] != "TNULL" else np.nan
    d["l1"] = float(np.abs(a["vec"] - b["vec"]).mean())
    d["l2"] = float(np.linalg.norm(a["vec"] - b["vec"]))
    d["cosine"] = float(1 - a["vec"] @ b["vec"] / (np.linalg.norm(a["vec"]) * np.linalg.norm(b["vec"]) + 1e-9))
    return d


def best_threshold(pos: np.ndarray, neg: np.ndarray):
    """Threshold t (match if distance <= t) with the best accuracy on positives vs negatives."""
    pos, neg = pos[~np.isnan(pos)], neg[~np.isnan(neg)]
    best = (np.nan, 0.0, 0.0, 0.0)
    for t in np.unique(np.concatenate([pos, neg])):
        tpr, tnr = (pos <= t).mean(), (neg > t).mean()
        acc = (tpr + tnr) / 2  # balanced accuracy: there are many more positives than negatives
        if acc > best[1]:
            best = (float(t), acc, tpr, 1 - tnr)
    return best  # threshold, accuracy, true positive rate, false positive rate


def main():
    variants = json.loads((DATA / "variants" / "variants.json").read_text())
    orig = {t: features(f) for t, f in frames(DATA / "variants" / "base_A.mp4").items()}
    rows = []
    for name in ALIGNED:
        for t, f in frames(Path(variants[name]["file"])).items():
            if t in orig:
                rows.append({"pair": "positive", "variant": name, **distances(orig[t], features(f))})
        print("done", name)
    b = list(frames(DATA / "variants" / "base_B.mp4").values())
    for i, (t, fa) in enumerate(orig.items()):
        rows.append({"pair": "negative", "variant": "tripA_vs_tripB", **distances(fa, features(b[i % len(b)]))})

    df = pd.DataFrame(rows)
    df.to_csv(RES / "metrics.csv", index=False)
    metrics = [c for c in df.columns if c not in ("pair", "variant")]

    # mean distance per variant (rows) and metric (columns)
    df.groupby("variant")[metrics].mean().round(3).to_csv(RES / "mean_distance_per_variant.csv")

    th = []
    pos, neg = df[df.pair == "positive"], df[df.pair == "negative"]
    for m in metrics:
        t, acc, tpr, fpr = best_threshold(pos[m].to_numpy(float), neg[m].to_numpy(float))
        th.append({"metric": m, "threshold": t, "accuracy": round(acc, 3), "tpr": round(tpr, 3), "fpr": round(fpr, 3),
                   "mean_positive": round(pos[m].mean(), 3), "mean_negative": round(neg[m].mean(), 3)})
        plt.figure(figsize=(5, 3))
        plt.hist(pos[m].dropna(), bins=30, alpha=0.6, label="same content")
        plt.hist(neg[m].dropna(), bins=30, alpha=0.6, label="other trip")
        plt.axvline(t, color="k", linestyle="--", label=f"threshold {t:g}")
        plt.title(m)
        plt.legend()
        plt.tight_layout()
        plt.savefig(RES / f"hist_{m}.png")
        plt.close()
    th = pd.DataFrame(th).sort_values("accuracy", ascending=False)
    th.to_csv(RES / "thresholds.csv", index=False)
    print(th.to_string(index=False))

    t = int(th.set_index("metric").loc["phash_hamming", "threshold"])
    (ROOT.parent / "decoder" / "thresholds.json").write_text(json.dumps({"phash": t}) + "\n")
    print(f"pHash threshold {t} -> decoder/thresholds.json")


if __name__ == "__main__":
    main()
