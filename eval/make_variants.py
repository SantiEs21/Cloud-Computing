"""Creates the test variants of trip A (one per transformation from the assignment).

Usage: python eval/make_variants.py eval/data/tripA.mp4 eval/data/tripB.mp4
Output: eval/data/variants/<name>.mp4  (+ variants.json with what each one is expected to give)
Needs the `ffmpeg` command. Salt-and-pepper and Gaussian noise are done with OpenCV.
The inputs are first converted to 720p "base" copies (4K would make every step very slow; the
hashes work on 32x32 images, so the resolution of the base does not matter).
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

OUT = Path(sys.argv[1]).parent / "variants"
OUT.mkdir(exist_ok=True)


def base(src: Path, name: str) -> Path:
    out = OUT / f"{name}.mp4"
    if not out.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", "scale=-2:720",
                        "-c:v", "libx264", "-crf", "18", "-an", str(out)], check=True)
    return out


A, B = base(Path(sys.argv[1]), "base_A"), base(Path(sys.argv[2]), "base_B")
FPS = cv2.VideoCapture(str(A)).get(cv2.CAP_PROP_FPS)


def duration(path: Path) -> float:
    cap = cv2.VideoCapture(str(path))
    d = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    return d


def ff(name: str, *args: str, src: Path = A):
    """One ffmpeg call; output re-encoded to H.264 unless the args choose another codec."""
    out = OUT / f"{name}.mp4"
    codec = [] if "-c:v" in args else ["-c:v", "libx264", "-crf", "23"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), *args, *codec, "-an", str(out)]
    subprocess.run(cmd, check=True)
    return out


def per_frame(name: str, fn):
    """Applies fn(frame) to every frame with OpenCV, then re-encodes with ffmpeg (H.264)."""
    cap = cv2.VideoCapture(str(A))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w, h = int(cap.get(3)), int(cap.get(4))
    raw = OUT / f"{name}.raw.avi"
    wr = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    while True:
        ok, f = cap.read()
        if not ok:
            break
        wr.write(fn(f))
    wr.release()
    cap.release()
    ff(name, src=raw)
    raw.unlink()


rng = np.random.default_rng(0)


def salt_pepper(f, amount=0.05):
    f = f.copy()
    m = rng.random(f.shape[:2])
    f[m < amount / 2] = 0
    f[m > 1 - amount / 2] = 255
    return f


def gaussian(f, sigma=15):
    return np.clip(f + rng.normal(0, sigma, f.shape), 0, 255).astype(np.uint8)


def logo(f):
    f = f.copy()
    h, w = f.shape[:2]
    cv2.rectangle(f, (w - w // 4, 20), (w - 20, 20 + h // 8), (255, 255, 255), -1)
    cv2.putText(f, "LOGO", (w - w // 4 + 10, 20 + h // 10), cv2.FONT_HERSHEY_SIMPLEX, h / 400, (0, 0, 255), 3)
    return f


d = duration(A)
mid = d / 2
# expected: what a correct decoder should answer for each variant
V = {}
V["original"] = (ff("original"), "AUTHENTIC")
V["trim_start"] = (ff("trim_start", "-ss", "10"), "AUTHENTIC")                       # first 10 s removed
V["trim_end"] = (ff("trim_end", "-t", f"{d - 10:.2f}"), "AUTHENTIC")                 # last 10 s removed
V["extract_middle"] = (ff("extract_middle", "-ss", f"{mid - 10:.2f}", "-t", "20"), "AUTHENTIC")
V["shift_black_3s"] = (ff("shift_black_3s", "-vf", "tpad=start_duration=3:color=black"), "MODIFIED")
V["speed_1_05"] = (ff("speed_1_05", "-vf", "setpts=PTS/1.05"), "MODIFIED")
V["fps_10"] = (ff("fps_10", "-vf", "fps=10"), "AUTHENTIC")
V["delete_1s"] = (ff("delete_1s", "-vf", f"select='not(between(t,{mid:.2f},{mid + 1:.2f}))',setpts=N/FRAME_RATE/TB"), "MODIFIED")
V["duplicate_1s"] = (ff("duplicate_1s", "-vf", f"loop=loop=1:size={round(FPS)}:start={round(mid * FPS)},setpts=N/FRAME_RATE/TB"), "MODIFIED")
V["h265"] = (ff("h265", "-c:v", "libx265", "-crf", "28", "-tag:v", "hvc1"), "AUTHENTIC")
V["bitrate_300k"] = (ff("bitrate_300k", "-c:v", "libx264", "-b:v", "300k"), "AUTHENTIC")
V["res_640x360"] = (ff("res_640x360", "-vf", "scale=640:360"), "AUTHENTIC")
V["crf_40"] = (ff("crf_40", "-c:v", "libx264", "-crf", "40"), "AUTHENTIC")
V["brightness_0_2"] = (ff("brightness_0_2", "-vf", "eq=brightness=0.2"), "AUTHENTIC")
V["contrast_1_5"] = (ff("contrast_1_5", "-vf", "eq=contrast=1.5"), "AUTHENTIC")
per_frame("salt_pepper_5", salt_pepper)
V["salt_pepper_5"] = (OUT / "salt_pepper_5.mp4", "AUTHENTIC")
per_frame("gaussian_noise", gaussian)
V["gaussian_noise"] = (OUT / "gaussian_noise.mp4", "AUTHENTIC")
per_frame("logo", logo)
V["logo"] = (OUT / "logo.mp4", "AUTHENTIC")
V["crop_80"] = (ff("crop_80", "-vf", "crop=iw*0.8:ih*0.8"), "AUTHENTIC")  # same content; hard for pHash
V["other_trip"] = (ff("other_trip", src=B), "NO MATCH")
# partial replacement: A with 5 s of B in the middle
V["partial_replace"] = (ff("partial_replace", "-i", str(B), "-filter_complex",
                           f"[0:v]trim=0:{mid:.2f},setpts=PTS-STARTPTS,scale=1280:720,setsar=1[a1];"
                           f"[1:v]trim=0:5,setpts=PTS-STARTPTS,scale=1280:720,setsar=1[b];"
                           f"[0:v]trim={mid + 5:.2f},setpts=PTS-STARTPTS,scale=1280:720,setsar=1[a2];"
                           f"[a1][b][a2]concat=n=3:v=1:a=0"), "MODIFIED")

json.dump({k: {"file": str(p), "expected": e} for k, (p, e) in V.items()},
          open(OUT / "variants.json", "w"), indent=1)
print(f"{len(V)} variants in {OUT}")
