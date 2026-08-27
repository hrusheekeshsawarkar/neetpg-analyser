#!/usr/bin/env python3
"""
Extra analyses: year drift, ask-type mix, cross-subject overlaps, due-for-return brief.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from mbbs_taxonomy import MBBS_SUBJECTS
from predict_priority import expand_topic_rows, is_real_topic, score_topics

DATA = Path("analysis/data/merged_questions.json")
PLOTS = Path("analysis/plots")
REPORTS = Path("analysis/reports")


def year_drift(df: pd.DataFrame) -> pd.DataFrame:
    """Compare recent (2021–2025) vs older (≤2020) topic shares."""
    recent = df[df["year"] >= 2021]
    older = df[df["year"] <= 2020]
    if recent.empty or older.empty:
        return pd.DataFrame()
    r = recent.groupby("topic")["qid"].nunique()
    o = older.groupby("topic")["qid"].nunique()
    r_share = r / r.sum()
    o_share = o / o.sum()
    out = pd.DataFrame({"recent_count": r, "older_count": o}).fillna(0)
    out["recent_share"] = out.index.map(lambda t: r_share.get(t, 0))
    out["older_share"] = out.index.map(lambda t: o_share.get(t, 0))
    out["delta_share"] = out["recent_share"] - out["older_share"]
    out["topic"] = out.index
    return out.sort_values("delta_share", ascending=False).reset_index(drop=True)


def ask_type_by_subject(qs: list[dict]) -> pd.DataFrame:
    rows = []
    for q in qs:
        subj = q.get("subject_clean") or "Unknown"
        if subj not in MBBS_SUBJECTS:
            continue
        ask = q.get("ask_type") or "other"
        rows.append({"subject": subj, "ask_type": ask})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return (
        df.groupby(["subject", "ask_type"])
        .size()
        .reset_index(name="count")
        .sort_values(["subject", "count"], ascending=[True, False])
    )


def write_due_brief(importance: pd.DataFrame, path: Path):
    due = importance[importance["due_for_return"]].head(40)
    lines = [
        "# Topics due for return",
        "",
        "> High-recurrence topics not seen in the most recent exam year(s) — revision candidates, not predictions.",
        "",
        "| Topic | Subject | Score | Last seen | Gap (yrs) | Count |",
        "|-------|---------|------:|----------:|----------:|------:|",
    ]
    for _, r in due.iterrows():
        lines.append(
            f"| {r['topic']} | {r['primary_subject']} | {r['importance_score']} | "
            f"{r['year_list'].split(',')[-1] if r['year_list'] else '?'} | "
            f"{r['years_since_last']} | {r['question_count']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_drift_md(drift: pd.DataFrame, path: Path):
    lines = [
        "# Topic year drift (2021–2025 vs ≤2020)",
        "",
        "## Rising in recent years",
        "",
        "| Topic | Δ share | Recent n | Older n |",
        "|-------|--------:|---------:|--------:|",
    ]
    for _, r in drift.head(25).iterrows():
        lines.append(
            f"| {r['topic']} | {r['delta_share']:+.4f} | {int(r['recent_count'])} | {int(r['older_count'])} |"
        )
    lines += ["", "## Falling vs older years", ""]
    lines += [
        "| Topic | Δ share | Recent n | Older n |",
        "|-------|--------:|---------:|--------:|",
    ]
    for _, r in drift.tail(25).iloc[::-1].iterrows():
        lines.append(
            f"| {r['topic']} | {r['delta_share']:+.4f} | {int(r['recent_count'])} | {int(r['older_count'])} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_drift(drift: pd.DataFrame):
    if drift.empty:
        return
    top = pd.concat([drift.head(15), drift.tail(15)])
    fig, ax = plt.subplots(figsize=(10, 10))
    colors = ["#27ae60" if x > 0 else "#c0392b" for x in top["delta_share"]]
    ax.barh(top["topic"], top["delta_share"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Change in share (recent − older)")
    ax.set_title("Topic drift: rising (green) vs falling (red)")
    plt.tight_layout()
    fig.savefig(PLOTS / "topic_year_drift.png", dpi=160, bbox_inches="tight")
    plt.close()


def plot_ask_type(ask: pd.DataFrame):
    if ask.empty:
        return
    # top ask types overall
    pivot = ask.pivot_table(index="subject", columns="ask_type", values="count", fill_value=0)
    # keep subjects with most questions
    order = pivot.sum(axis=1).sort_values(ascending=False).head(12).index
    pivot = pivot.loc[order]
    fig, ax = plt.subplots(figsize=(12, 7))
    pivot.plot(kind="bar", stacked=True, ax=ax, colormap="tab20", width=0.85)
    ax.set_ylabel("Questions")
    ax.set_title("Ask-type mix by subject (top 12 subjects)")
    ax.legend(title="Ask type", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    plt.tight_layout()
    fig.savefig(PLOTS / "ask_type_by_subject.png", dpi=160, bbox_inches="tight")
    plt.close()


def main():
    PLOTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    qs = json.load(open(DATA))
    df = expand_topic_rows(qs)
    importance = score_topics(df)

    drift = year_drift(df)
    if len(drift):
        drift.to_csv(PLOTS / "topic_year_drift.csv", index=False)
        write_drift_md(drift, REPORTS / "topic_year_drift.md")
        plot_drift(drift)
        print("Saved topic year drift")

    ask = ask_type_by_subject(qs)
    if len(ask):
        ask.to_csv(PLOTS / "ask_type_by_subject.csv", index=False)
        plot_ask_type(ask)
        print("Saved ask-type by subject")

    # overlaps already in predict; refresh a short markdown
    from predict_priority import overlap_stats

    overlaps = overlap_stats(qs)
    if len(overlaps):
        overlaps.head(50).to_csv(PLOTS / "multi_topic_overlaps_top50.csv", index=False)
        lines = [
            "# Top multi-topic / multi-subject co-occurrences",
            "",
            "| Item A | Item B | Count |",
            "|--------|--------|------:|",
        ]
        for _, r in overlaps.head(40).iterrows():
            lines.append(f"| {r['item_a']} | {r['item_b']} | {r['co_occurrence']} |")
        (REPORTS / "topic_overlaps.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Saved overlaps brief")

    write_due_brief(importance, REPORTS / "topics_due_for_return.md")
    print("Saved due-for-return brief")
    print("Done → analysis/reports/ + analysis/plots/")


if __name__ == "__main__":
    main()
