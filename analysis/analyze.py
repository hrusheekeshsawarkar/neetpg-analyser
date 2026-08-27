#!/usr/bin/env python3
"""Core NEET PG frequency charts — all 19 MBBS subjects, readable layouts."""

from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from mbbs_taxonomy import MBBS_SUBJECTS

os.environ.setdefault("MPLCONFIGDIR", str(Path(".mplconfig").resolve()))

with open("analysis/data/merged_questions.json") as f:
    qs = json.load(f)

df = pd.DataFrame(qs)
df = df[df["subject_clean"].isin(MBBS_SUBJECTS)].copy()
df["topic_clean"] = df["topic_clean"].fillna("").astype(str)
df.loc[
    df["topic_clean"].str.lower().isin(["general", "unknown", "others", "mixed", ""]),
    "topic_clean",
] = ""
df_topics = df[df["topic_clean"].str.len() > 0].copy()

year_min, year_max = int(df["year"].min()), int(df["year"].max())
n_q = len(df)
sns.set_style("whitegrid")
Path("analysis/plots").mkdir(parents=True, exist_ok=True)

# Stable palette by subject order
palette = sns.color_palette("husl", len(MBBS_SUBJECTS))
pal = dict(zip(MBBS_SUBJECTS, palette))

# ----- 4-panel overview (less clutter) -----
fig, axes = plt.subplots(2, 2, figsize=(18, 14))

ax1 = axes[0, 0]
sc = df["subject_clean"].value_counts().reindex(MBBS_SUBJECTS).fillna(0).astype(int)
sc = sc[sc > 0].sort_values(ascending=True)
bars = ax1.barh(sc.index, sc.values, color=[pal.get(s, "#888") for s in sc.index])
ax1.set_xlabel("Questions")
ax1.set_title(f"Questions per subject ({year_min}–{year_max}, n={n_q})", fontweight="bold")
for bar, val in zip(bars, sc.values):
    ax1.text(val + max(sc.values) * 0.01, bar.get_y() + bar.get_height() / 2, str(int(val)), va="center", fontsize=8)

ax2 = axes[0, 1]
# Top 8 subjects by year; rest → Other (keeps legend readable)
top8 = df["subject_clean"].value_counts().head(8).index.tolist()
df_y = df.copy()
df_y["subj_plot"] = df_y["subject_clean"].where(df_y["subject_clean"].isin(top8), "Other")
ys = df_y.groupby(["year", "subj_plot"]).size().unstack(fill_value=0)
ys = ys.loc[sorted(ys.index)]
cols = [c for c in top8 if c in ys.columns] + (["Other"] if "Other" in ys.columns else [])
ys[cols].plot(kind="bar", ax=ax2, width=0.85, stacked=False, colormap="tab10", legend=True)
ax2.set_xlabel("Year")
ax2.set_ylabel("Questions")
ax2.set_title("Subject mix by year (top 8 + Other)", fontweight="bold")
ax2.legend(title="Subject", fontsize=7, loc="upper left")
ax2.tick_params(axis="x", rotation=45)

ax3 = axes[1, 0]
top_topics = df_topics["topic_clean"].value_counts().head(12).index.tolist()
df_top = df_topics[df_topics["topic_clean"].isin(top_topics)]
hm_data = df_top.groupby(["year", "topic_clean"]).size().unstack(fill_value=0)
hm_data = hm_data.loc[sorted(hm_data.index), [t for t in top_topics if t in hm_data.columns]]
sns.heatmap(hm_data.T, annot=True, fmt="d", cmap="YlOrRd", ax=ax3, linewidths=0.3, annot_kws={"size": 7})
ax3.set_title("Top 12 topics × year", fontweight="bold")
ax3.set_xlabel("Year")
ax3.set_ylabel("")

ax4 = axes[1, 1]
topic_counts = df_topics["topic_clean"].value_counts()
cum_pct = topic_counts.cumsum() / topic_counts.sum() * 100
n_pareto = int((cum_pct <= 80).sum() + 1)
n_pareto = min(n_pareto, len(topic_counts))
# Show enough of the curve that 80% is visible (with a little headroom)
x_max = min(len(topic_counts), max(n_pareto + max(20, n_pareto // 10), 50))
xs = list(range(1, x_max + 1))
ys = cum_pct.values[:x_max]
ax4.fill_between(xs, 0, ys, alpha=0.25, color="steelblue")
ax4.plot(xs, ys, color="steelblue", linewidth=2)
ax4.axhline(80, color="crimson", linestyle="--", linewidth=1.2, label="80%")
if n_pareto <= x_max:
    ax4.axvline(n_pareto, color="orange", linestyle="--", linewidth=1.2, label=f"{n_pareto} topics")
    ax4.annotate(
        f"{n_pareto} topics → 80%",
        xy=(n_pareto, 80),
        xytext=(min(n_pareto + x_max * 0.05, x_max * 0.7), 55),
        fontsize=8,
        arrowprops=dict(arrowstyle="->", color="gray"),
    )
ax4.set_xlabel("Topics (ranked)")
ax4.set_ylabel("Cumulative %")
ax4.set_title(f"Pareto: {n_pareto}/{len(topic_counts)} topics = 80%", fontweight="bold")
ax4.legend(fontsize=8)
ax4.set_xlim(1, x_max)
ax4.set_ylim(0, 105)

plt.tight_layout()
plt.savefig("analysis/plots/neetpg_analysis.png", dpi=160, bbox_inches="tight")
plt.close()
print("Saved: analysis/plots/neetpg_analysis.png")

# ----- Trends -----
fig2, ax = plt.subplots(figsize=(12, 6))
years_order = sorted(df_topics["year"].unique())
trend_topics = df_topics["topic_clean"].value_counts().head(8).index.tolist()
for i, topic in enumerate(trend_topics):
    vals = [
        len(df_topics[(df_topics["year"] == y) & (df_topics["topic_clean"] == topic)])
        for y in years_order
    ]
    ax.plot(years_order, vals, marker="o", linewidth=2, label=topic, color=palette[i % len(palette)])
ax.set_xlabel("Year")
ax.set_ylabel("Questions")
ax.set_title("Topic trends (top 8)", fontweight="bold")
ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
ax.set_xticks(years_order)
plt.tight_layout()
plt.savefig("analysis/plots/neetpg_trends.png", dpi=160, bbox_inches="tight")
plt.close()
print("Saved: analysis/plots/neetpg_trends.png")

# ----- ALL subjects bar (replaces truncated pie) -----
fig3, ax3p = plt.subplots(figsize=(10, 9))
scp = df["subject_clean"].value_counts().reindex(MBBS_SUBJECTS).fillna(0).astype(int)
scp = scp[scp > 0].sort_values(ascending=True)
ax3p.barh(scp.index, scp.values, color=[pal.get(s, "#888") for s in scp.index])
for y, v in enumerate(scp.values):
    ax3p.text(v + max(scp.values) * 0.01, y, f"{int(v)} ({100*v/scp.sum():.1f}%)", va="center", fontsize=8)
ax3p.set_xlabel("Questions")
ax3p.set_title(f"All MBBS subjects ({year_min}–{year_max}) — includes OBG", fontweight="bold")
plt.tight_layout()
plt.savefig("analysis/plots/neetpg_pie.png", dpi=160, bbox_inches="tight")
plt.close()
print("Saved: analysis/plots/neetpg_pie.png (full subject bar; was truncated pie)")

# Also a true pie with ALL subjects + legend (no label overcrowding on wedges)
fig4, ax4p = plt.subplots(figsize=(11, 8))
scp2 = df["subject_clean"].value_counts().reindex(MBBS_SUBJECTS).fillna(0).astype(int)
scp2 = scp2[scp2 > 0]
wedges, _ = ax4p.pie(scp2.values, startangle=90, colors=[pal.get(s, "#888") for s in scp2.index])
ax4p.legend(
    wedges,
    [f"{s} ({int(c)})" for s, c in scp2.items()],
    title="Subject",
    loc="center left",
    bbox_to_anchor=(1.0, 0.5),
    fontsize=8,
)
ax4p.set_title(f"Subject share — all {len(scp2)} taught subjects", fontweight="bold")
plt.tight_layout()
plt.savefig("analysis/plots/neetpg_subject_pie_full.png", dpi=160, bbox_inches="tight")
plt.close()
print("Saved: analysis/plots/neetpg_subject_pie_full.png")

year_subj = df.groupby(["year", "subject_clean"]).size().unstack(fill_value=0)
year_subj.to_csv("analysis/plots/year_subject_matrix.csv")
topic_counts.to_csv("analysis/plots/topic_frequency.csv")
df.to_csv("analysis/data/analysis_ready.csv", index=False)
print("Saved CSVs + analysis_ready.csv")
