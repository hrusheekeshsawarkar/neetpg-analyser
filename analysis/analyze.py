import json, pandas as pd, numpy as np, matplotlib.pyplot as plt, seaborn as sns, os

with open("analysis/data/merged_questions.json") as f:
    qs = json.load(f)

df = pd.DataFrame(qs)
df = df[df["subject_clean"] != "Unknown"]

sns.set_style("whitegrid")
os.makedirs("analysis/plots", exist_ok=True)

palette = sns.color_palette("husl", 20)
pal = dict(zip(df["subject_clean"].value_counts().index, palette))

fig, axes = plt.subplots(2, 2, figsize=(16, 14))

ax1 = axes[0, 0]
sc = df["subject_clean"].value_counts()
bars = ax1.barh(
    sc.index[::-1], sc.values[::-1], color=[pal.get(s, "#888") for s in sc.index[::-1]]
)
ax1.set_xlabel("Number of Questions")
ax1.set_title(
    "Questions per Subject (2021-2025, n=728)", fontsize=13, fontweight="bold"
)
for bar, val in zip(bars, sc.values[::-1]):
    ax1.text(
        val + 0.5, bar.get_y() + bar.get_height() / 2, str(val), va="center", fontsize=9
    )

ax2 = axes[0, 1]
year_order = sorted(df["year"].unique())
ys = df.groupby(["year", "subject_clean"]).size().unstack(fill_value=0)
ys = ys.loc[year_order, ys.sum().sort_values(ascending=False).index]
ys.plot(kind="bar", ax=ax2, width=0.85, colormap="tab20", edgecolor="none")
ax2.set_xlabel("Year")
ax2.set_ylabel("Number of Questions")
ax2.set_title("Subject Distribution by Year", fontsize=13, fontweight="bold")
ax2.legend(title="Subject", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=7)
ax2.tick_params(axis="x", rotation=0)

ax3 = axes[1, 0]
top_topics = df["topic_clean"].value_counts().head(15).index.tolist()
df_top = df[df["topic_clean"].isin(top_topics)]
hm_data = df_top.groupby(["year", "topic_clean"]).size().unstack(fill_value=0)
hm_data = hm_data.loc[
    sorted(hm_data.index), [t for t in top_topics if t in hm_data.columns]
]
sns.heatmap(
    hm_data.T,
    annot=True,
    fmt="d",
    cmap="YlOrRd",
    ax=ax3,
    cbar_kws={"label": "Questions"},
    linewidths=0.5,
)
ax3.set_title(
    "Topic Frequency Heatmap by Year (Top 15 Topics)", fontsize=13, fontweight="bold"
)
ax3.set_xlabel("Year")
ax3.set_ylabel("Topic")

ax4 = axes[1, 1]
topic_counts = df["topic_clean"].value_counts()
cum_pct = topic_counts.cumsum() / topic_counts.sum() * 100
n_pareto = (cum_pct <= 80).sum() + 1
xrange = range(1, len(topic_counts) + 1)
ax4.fill_between(xrange, 0, cum_pct.values, alpha=0.3, color="steelblue")
ax4.plot(xrange, cum_pct.values, color="steelblue", linewidth=2)
ax4.axhline(80, color="red", linestyle="--", linewidth=1.5, label="80% threshold")
ax4.axvline(
    n_pareto,
    color="orange",
    linestyle="--",
    linewidth=1.5,
    label=str(n_pareto) + " topics",
)
ax4.set_xlabel("Number of Topics (ranked)")
ax4.set_ylabel("Cumulative % of Questions")
ax4.set_title(
    str(n_pareto) + "/" + str(len(topic_counts)) + " topics = 80% of questions",
    fontsize=13,
    fontweight="bold",
)
ax4.legend()
ax4.set_xlim(1, len(topic_counts))

plt.tight_layout()
plt.savefig("analysis/plots/neetpg_analysis.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: analysis/plots/neetpg_analysis.png")

fig2, ax = plt.subplots(figsize=(12, 6))
years_order = sorted(df["year"].unique())
trend_topics = df["topic_clean"].value_counts().head(10).index.tolist()
for i, topic in enumerate(trend_topics):
    vals = [
        len(df[(df["year"] == y) & (df["topic_clean"] == topic)]) for y in years_order
    ]
    ax.plot(years_order, vals, marker="o", linewidth=2, label=topic, color=palette[i])
ax.set_xlabel("Year")
ax.set_ylabel("Number of Questions")
ax.set_title(
    "Topic Frequency Trends by Year (Top 10 Topics)", fontsize=13, fontweight="bold"
)
ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
ax.set_xticks(years_order)
plt.tight_layout()
plt.savefig("analysis/plots/neetpg_trends.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: analysis/plots/neetpg_trends.png")

fig3, ax3p = plt.subplots(figsize=(10, 10))
scp = df["subject_clean"].value_counts()
top = scp.head(10)
other_sum = scp.iloc[10:].sum()
labels = top.index.tolist() + (["Other Subjects"] if other_sum > 0 else [])
sizes = top.values.tolist() + ([other_sum] if other_sum > 0 else [])
explode = [0.03] * len(labels)
ax3p.pie(
    sizes,
    labels=labels,
    autopct="%1.1f%%",
    startangle=140,
    explode=explode,
    pctdistance=0.8,
)
ax3p.set_title("Subject Distribution (Pie Chart)", fontsize=13, fontweight="bold")
plt.savefig("analysis/plots/neetpg_pie.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: analysis/plots/neetpg_pie.png")

year_subj = df.groupby(["year", "subject_clean"]).size().unstack(fill_value=0)
year_subj.to_csv("analysis/plots/year_subject_matrix.csv")
topic_counts.to_csv("analysis/plots/topic_frequency.csv")
print("Saved CSVs")

df.to_csv("analysis/data/analysis_ready.csv", index=False)
print("Saved: analysis/data/analysis_ready.csv")
