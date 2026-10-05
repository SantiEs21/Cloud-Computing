"""Runs the real decoder matching on every variant against trip A's hashes stored in Supabase
(the hashes the browser encoder sent), and writes results/video_eval.csv + .md.

Usage: python eval/video_eval.py <trip A id or its first 8 chars>
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

from decoder.main import THRESHOLD, stored_samples
from decoder.matching import match, video_samples

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)


def main(prefix: str):
    trips = stored_samples(None)
    trip_id = next(t for t in trips if t.startswith(prefix))
    stored = trips[trip_id]
    variants = json.loads((ROOT / "data" / "variants" / "variants.json").read_text())

    rows = []
    for name, v in variants.items():
        t0 = time.perf_counter()
        r = match(video_samples(v["file"]), stored, THRESHOLD)
        ms = round((time.perf_counter() - t0) * 1000)
        rows.append({
            "variant": name, "expected": v["expected"], "verdict": r["verdict"],
            "correct": r["verdict"] == v["expected"], "matched_pct": r["matched_pct"],
            "mean_distance": r["mean_distance"], "position_s": r["position_s"],
            "modified_sections": "; ".join(f"{s['from_s']}-{s['to_s']} s" for s in r["modified_sections"]) or "-",
            "samples": r["samples"], "time_ms": ms,
        })
        print(rows[-1])

    df = pd.DataFrame(rows)
    df.to_csv(RES / "video_eval.csv", index=False)

    found = df.verdict != "NO MATCH"
    should = df.expected != "NO MATCH"
    summary = {
        "variants": len(df),
        "correct verdicts": int(df.correct.sum()),
        "true matches (trip recognised when it should be)": int((found & should).sum()),
        "missed matches (NO MATCH but same trip)": int((~found & should).sum()),
        "false matches (recognised but other trip)": int((found & ~should).sum()),
        "modifications detected (expected MODIFIED -> MODIFIED)":
            f"{int(((df.expected == 'MODIFIED') & (df.verdict == 'MODIFIED')).sum())} / {int((df.expected == 'MODIFIED').sum())}",
        "pHash threshold (bits)": THRESHOLD,
    }
    md = ["# Video evaluation (decoder vs trip A)", "", f"Trip A: `{trip_id}`", "",
          df.to_markdown(index=False), "", "## Summary", ""]
    md += [f"- {k}: **{v}**" for k, v in summary.items()]
    (RES / "video_eval.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[-len(summary):]))


if __name__ == "__main__":
    main(sys.argv[1])
