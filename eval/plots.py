"""Figures for docs/report.md, from real results:
- results/video_eval_matched.png: % matched samples per variant (from results/video_eval.csv)
- results/network_arrival.png: when fingerprint rows reached Supabase, online vs offline trip

Usage: python -m eval.plots [online_trip_prefix] [offline_trip_prefix]
"""
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RES = Path(__file__).resolve().parent / "results"
BLUE, ORANGE = "#2a78d6", "#eb6834"  # blue / orange: distinguishable also with colour blindness
INK, MUTED, GRID = "#222222", "#6b6b6b", "#e4e4e0"


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=INK)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def video_eval_chart():
    df = pd.read_csv(RES / "video_eval.csv").iloc[::-1]  # first variant on top
    fig, ax = plt.subplots(figsize=(7.5, 6.2))
    style(ax)
    ax.grid(axis="y", visible=False)
    ax.barh(df.variant, df.matched_pct, color=BLUE, height=0.6)
    for x, label in ((30, "NO MATCH < 30 %"), (90, "AUTHENTIC ≥ 90 %")):
        ax.axvline(x, color=MUTED, linestyle="--", linewidth=1)
        ax.text(x - 1, len(df) - 0.3, label, color=MUTED, fontsize=8, ha="right", va="bottom")
    # Selective labels: only bars below 100 %, plus the one wrong verdict
    for i, r in enumerate(df.itertuples()):
        if r.matched_pct < 100:
            note = f"{r.matched_pct:g} % · {r.verdict}" + ("  ✗ expected " + r.expected if not r.correct else "")
            ax.text(r.matched_pct + 1, i, note, va="center", fontsize=8, color=INK)
    ax.set_xlim(0, 135)
    ax.set_xticks([0, 30, 60, 90, 100])
    ax.set_xlabel("Matched samples (%)", color=INK)
    ax.set_title("Decoder vs trip A: matched samples per variant", color=INK, loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(RES / "video_eval_matched.png", dpi=160)
    plt.close(fig)


def network_chart(online: str, offline: str):
    from decoder.main import db, fetch_all  # needs decoder/.env (Supabase)

    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    style(ax)
    for prefix, color, name in ((online, BLUE, "online"), (offline, ORANGE, "network off, then reconnect")):
        trip = next(t for t in db.table("trips").select("id,started_at").execute().data if t["id"].startswith(prefix))
        start = datetime.fromisoformat(trip["started_at"])
        rows = fetch_all(lambda: db.table("fingerprints").select("created_at").eq("trip_id", trip["id"]).order("created_at"))
        secs = [(datetime.fromisoformat(r["created_at"]) - start).total_seconds() for r in rows]
        ax.step(secs, range(1, len(secs) + 1), where="post", color=color, linewidth=2, label=f"{name} ({prefix})")
        if prefix == offline:  # direct label for the jump
            ax.text(secs[-1] - 4, len(secs) / 2, f"{name}\n{len(secs)} rows arrive at {secs[-1]:.0f} s",
                    color=INK, fontsize=8, va="center", ha="right")
    ax.set_xlabel("Seconds since the trip started", color=INK)
    ax.set_ylabel("Fingerprint rows on server", color=INK)
    ax.set_title("When hashes reach Supabase", color=INK, loc="left", fontsize=11)
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0.33, 1))  # clear of the lines
    fig.tight_layout()
    fig.savefig(RES / "network_arrival.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    video_eval_chart()
    if len(sys.argv) == 3:
        network_chart(sys.argv[1], sys.argv[2])
    print("figures written to", RES)
