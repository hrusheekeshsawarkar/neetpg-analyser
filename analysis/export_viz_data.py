#!/usr/bin/env python3
"""
Export UI-ready viz aggregates + regenerate improved static plots.

Outputs under analysis/plots/:
  - subject_totals.csv
  - top_concepts_clean.csv   (filters vignette-like LLM concepts)
  - ask_type_share.csv       (normalized ask-type mix by subject)
  - improved PNGs (heatmap, ask-type, concepts, subject overview)

Also syncs key CSVs into web/public/data/ when that folder exists.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from mbbs_taxonomy import MBBS_SUBJECTS

ROOT = Path(__file__).resolve().parents[1]  # repo root
ANALYSIS = Path(__file__).resolve().parent
DATA = ANALYSIS / "data" / "merged_questions.json"
PLOTS = ANALYSIS / "plots"
WEB_DATA = ROOT / "web" / "public" / "data"

os.environ.setdefault("MPLCONFIGDIR", str((ROOT / ".mplconfig").resolve()))

# Patient-stem style "concepts" are noise for revision packs / charts
VIGNETTE_RE = re.compile(
    r"^(a |an |the )?\d{1,3}[-\s]?year[- ]old|"
    r"^(a |an |the )?(male|female|man|woman|patient|boy|girl)\b|"
    r"\bpresented with\b|\bknown case of\b|\bcomplains of\b",
    re.I,
)


def load_df() -> pd.DataFrame:
    qs = json.loads(DATA.read_text())
    df = pd.DataFrame(qs)
    df = df[df["subject_clean"].isin(MBBS_SUBJECTS)].copy()
    df["topic_clean"] = df.get("topic_clean", pd.Series(dtype=str)).fillna("").astype(str)
    df.loc[
        df["topic_clean"].str.lower().isin(["general", "unknown", "others", "mixed", ""]),
        "topic_clean",
    ] = ""
    return df


def is_clean_concept(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 3 or len(t) > 55:
        return False
    if VIGNETTE_RE.search(t):
        return False
    if t.count(" ") > 8:
        return False
    return True


def export_csvs(df: pd.DataFrame) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)

    totals = (
        df["subject_clean"]
        .value_counts()
        .reindex(MBBS_SUBJECTS)
        .fillna(0)
        .astype(int)
        .reset_index()
    )
    totals.columns = ["subject", "question_count"]
    totals["share"] = totals["question_count"] / max(int(totals["question_count"].sum()), 1)
    totals.to_csv(PLOTS / "subject_totals.csv", index=False)

    # Clean concepts: prefer real short labels with count >= 2
    concepts = (
        df[df["concept"].fillna("").astype(str).str.len() > 0]
        .groupby(["topic_clean", "concept"], dropna=False)
        .size()
        .reset_index(name="count")
        .rename(columns={"topic_clean": "topic"})
    )
    concepts = concepts[concepts["concept"].map(is_clean_concept)]
    concepts = concepts[concepts["count"] >= 2].sort_values(
        ["topic", "count"], ascending=[True, False]
    )
    concepts.to_csv(PLOTS / "top_concepts_clean.csv", index=False)

    ask = (
        df[df["ask_type"].fillna("").astype(str).str.len() > 0]
        .groupby(["subject_clean", "ask_type"])
        .size()
        .reset_index(name="count")
        .rename(columns={"subject_clean": "subject"})
    )
    ask["share"] = ask["count"] / ask.groupby("subject")["count"].transform("sum")
    ask.to_csv(PLOTS / "ask_type_share.csv", index=False)

    print(f"  subject_totals: {len(totals)} rows")
    print(f"  top_concepts_clean: {len(concepts)} rows")
    print(f"  ask_type_share: {len(ask)} rows")


def style_dark_ish():
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "figure.facecolor": "white",
            "axes.facecolor": "#fafbfc",
        }
    )


def plot_subject_overview(df: pd.DataFrame) -> None:
    style_dark_ish()
    sc = df["subject_clean"].value_counts().reindex(MBBS_SUBJECTS).fillna(0).astype(int)
    sc = sc[sc > 0].sort_values(ascending=True)
    colors = sns.color_palette("crest", n_colors=len(sc))

    fig, ax = plt.subplots(figsize=(10, 8))
    bars = ax.barh(sc.index, sc.values, color=colors)
    ax.set_xlabel("Questions")
    ax.set_title(f"Questions per taught subject (n={len(df):,})")
    for bar, val in zip(bars, sc.values):
        ax.text(
            val + max(sc.values) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{int(val)}  ({100 * val / sc.sum():.1f}%)",
            va="center",
            fontsize=8,
        )
    ax.set_xlim(0, max(sc.values) * 1.22)
    plt.tight_layout()
    fig.savefig(PLOTS / "subject_totals.png", dpi=170, bbox_inches="tight")
    plt.close()
    print("  wrote subject_totals.png")


def plot_year_subject_heatmap(df: pd.DataFrame) -> None:
    style_dark_ish()
    mat = (
        df.groupby(["year", "subject_clean"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=MBBS_SUBJECTS, fill_value=0)
    )
    # Drop empty subjects
    mat = mat.loc[:, mat.sum() > 0]
    # Row-normalize to share within year (fairer across thin recent years)
    share = mat.div(mat.sum(axis=1).replace(0, np.nan), axis=0).fillna(0) * 100

    fig, ax = plt.subplots(figsize=(14, 7))
    sns.heatmap(
        share.T,
        cmap="YlGnBu",
        ax=ax,
        linewidths=0.3,
        linecolor="white",
        cbar_kws={"label": "% of that year's questions"},
        annot=False,
    )
    ax.set_title("Subject mix by year (% within year)")
    ax.set_xlabel("Year")
    ax.set_ylabel("")
    plt.tight_layout()
    fig.savefig(PLOTS / "year_subject_heatmap.png", dpi=170, bbox_inches="tight")
    plt.close()
    print("  wrote year_subject_heatmap.png")


def plot_ask_type_improved(df: pd.DataFrame) -> None:
    style_dark_ish()
    ask = (
        df[df["ask_type"].fillna("").astype(str).str.len() > 0]
        .groupby(["subject_clean", "ask_type"])
        .size()
        .reset_index(name="count")
    )
    if ask.empty:
        return
    pivot = ask.pivot_table(
        index="subject_clean", columns="ask_type", values="count", fill_value=0
    )
    order = pivot.sum(axis=1).sort_values(ascending=True).tail(12).index
    pivot = pivot.loc[order]
    # Drop tiny ask types
    keep = pivot.columns[pivot.sum() >= max(20, pivot.values.sum() * 0.02)]
    pivot = pivot[keep]
    # Normalize to 100% for comparable mix
    norm = pivot.div(pivot.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(11, 8))
    norm.plot(kind="barh", stacked=True, ax=ax, width=0.82, colormap="Set2")
    ax.set_xlabel("% of subject's labeled questions")
    ax.set_ylabel("")
    ax.set_title("Ask-type mix by subject (share, top 12)")
    ax.legend(title="Ask type", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax.set_xlim(0, 100)
    plt.tight_layout()
    fig.savefig(PLOTS / "ask_type_by_subject.png", dpi=170, bbox_inches="tight")
    plt.close()
    print("  wrote ask_type_by_subject.png (share, horizontal)")


def plot_concepts_improved(df: pd.DataFrame) -> None:
    style_dark_ish()
    # Top topics by volume among clean concepts
    concepts = (
        df[df["concept"].fillna("").map(is_clean_concept)]
        .groupby(["topic_clean", "concept"])
        .size()
        .reset_index(name="count")
        .rename(columns={"topic_clean": "topic"})
    )
    concepts = concepts[concepts["count"] >= 2]
    if concepts.empty:
        return
    top_topics = (
        concepts.groupby("topic")["count"].sum().sort_values(ascending=False).head(4).index.tolist()
    )
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    axes = axes.flatten()
    teal = "#0f766e"
    for ax, topic in zip(axes, top_topics):
        sub = concepts[concepts["topic"] == topic].sort_values("count", ascending=True).tail(6)
        ax.barh(sub["concept"], sub["count"], color=teal)
        ax.set_title(topic[:48], fontsize=11, fontweight="bold")
        ax.set_xlabel("Questions")
        ax.tick_params(axis="y", labelsize=8)
    for ax in axes[len(top_topics) :]:
        ax.axis("off")
    plt.suptitle("High-yield concepts within top topics (cleaned labels)", fontweight="bold")
    plt.tight_layout()
    fig.savefig(PLOTS / "within_topic_concepts.png", dpi=170, bbox_inches="tight")
    plt.close()
    print("  wrote within_topic_concepts.png")


def plot_importance_bands() -> None:
    path = PLOTS / "topic_importance.csv"
    if not path.exists():
        return
    style_dark_ish()
    imp = pd.read_csv(path)
    top = imp.head(30).iloc[::-1]
    colors = {
        "Must": "#c0392b",
        "High": "#e67e22",
        "Medium": "#2980b9",
        "Low": "#95a5a6",
    }
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.barh(
        top["topic"],
        top["importance_score"],
        color=[colors.get(b, "#888") for b in top["priority_band"]],
    )
    ax.set_xlabel("Importance score")
    ax.set_title("Topic importance — Must / High / Medium")
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=c) for c in ["#c0392b", "#e67e22", "#2980b9"]
    ]
    ax.legend(handles, ["Must", "High", "Medium"], loc="lower right")
    plt.tight_layout()
    fig.savefig(PLOTS / "topic_importance.png", dpi=170, bbox_inches="tight")
    plt.close()
    print("  wrote topic_importance.png")


def sync_web() -> None:
    if not WEB_DATA.exists():
        return
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    for name in [
        "subject_totals.csv",
        "top_concepts_clean.csv",
        "ask_type_share.csv",
        "year_subject_matrix.csv",
        "topic_importance.csv",
        "topic_year_drift.csv",
        "ask_type_by_subject.csv",
        "multi_topic_overlaps_top50.csv",
    ]:
        src = PLOTS / name
        if src.exists():
            shutil.copy2(src, WEB_DATA / name)
    # overlaps + drift aliases used by UI
    top50 = PLOTS / "multi_topic_overlaps_top50.csv"
    if top50.exists():
        shutil.copy2(top50, WEB_DATA / "overlaps.csv")
    drift = PLOTS / "topic_year_drift.csv"
    if drift.exists():
        shutil.copy2(drift, WEB_DATA / "drift.csv")
    print(f"  synced → {WEB_DATA}")


def main() -> None:
    print("Loading questions…")
    df = load_df()
    print(f"  n={len(df)}")
    export_csvs(df)
    plot_subject_overview(df)
    plot_year_subject_heatmap(df)
    plot_ask_type_improved(df)
    plot_concepts_improved(df)
    plot_importance_bands()
    # Ensure year_subject_matrix exists / refreshed
    mat = (
        df.groupby(["year", "subject_clean"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=[c for c in MBBS_SUBJECTS if c in df["subject_clean"].unique()], fill_value=0)
    )
    mat.to_csv(PLOTS / "year_subject_matrix.csv")
    sync_web()
    print("Done.")


if __name__ == "__main__":
    main()
