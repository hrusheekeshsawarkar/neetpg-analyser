#!/usr/bin/env python3
"""
Topic importance + next-exam priority forecasting (no local ML).

Inputs: analysis/data/merged_questions.json (prefer LLM-labeled fields:
  subject_clean, topic_clean, topics[], concept, ask_type, secondary_subjects)

Outputs under analysis/plots/ and analysis/reports/:
  - topic_importance.csv / .json
  - concept_frequency.csv
  - ask_type_by_topic.csv
  - next_exam_priorities.md / .json
  - multi_topic_overlaps.csv
  - importance_pareto.png, recurrence_heatmap.png, concept_bars.png
"""

from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Allow `python analysis/predict_priority.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mbbs_taxonomy import topic_to_subject_map  # noqa: E402
from topic_rules import TOPIC_RULES  # noqa: E402

DATA = Path("analysis/data/merged_questions.json")
PLOTS = Path("analysis/plots")
REPORTS = Path("analysis/reports")

FAKE_TOPICS = {"general", "unknown", "others", "mixed", "unclassified", ""}
FAKE_SUBJECTS = {"", "unknown", "general", "others", "mixed"}

# Prefer one subject when a topic name exists under multiple subjects in TOPIC_RULES
AMBIGUOUS_TOPIC_SUBJECT = {
    "Cardiovascular": "Physiology",
    "Trauma": "Orthopedics",
    "Toxicology": "Pharmacology",
    "Critical Care": "Medicine",
}


def _topic_to_subject() -> dict[str, str]:
    out = topic_to_subject_map()
    rev: dict[str, list[str]] = defaultdict(list)
    for subj, topics in TOPIC_RULES.items():
        for topic in topics:
            rev[topic].append(subj)
    for topic, subjects in rev.items():
        if topic in AMBIGUOUS_TOPIC_SUBJECT:
            out[topic] = AMBIGUOUS_TOPIC_SUBJECT[topic]
        elif topic not in out and len(subjects) == 1:
            out[topic] = subjects[0]
    return out


TOPIC_SUBJECT = _topic_to_subject()


def load_questions() -> list[dict]:
    with open(DATA) as f:
        return json.load(f)


def is_real_topic(t: str | None) -> bool:
    return bool(t) and t.strip().lower() not in FAKE_TOPICS


def resolve_subject(raw: str | None, topic: str | None = None) -> str:
    """Use labeled subject when real; otherwise infer from topic via TOPIC_RULES."""
    s = (raw or "").strip()
    if s and s.lower() not in FAKE_SUBJECTS:
        return s
    if topic and topic in TOPIC_SUBJECT:
        return TOPIC_SUBJECT[topic]
    return s or "Unknown"


def expand_topic_rows(qs: list[dict]) -> pd.DataFrame:
    """One row per (question, topic) including multi-topic overlaps."""
    rows = []
    for i, q in enumerate(qs):
        year = q.get("year")
        raw_subject = q.get("subject_clean") or q.get("subject") or ""
        primary = q.get("topic_clean") or q.get("topic") or ""
        topics = q.get("topics") or []
        if not isinstance(topics, list):
            topics = [topics]
        topics = [t for t in topics if is_real_topic(str(t))]
        if is_real_topic(primary) and primary not in topics:
            topics = [primary] + topics
        if not topics:
            continue
        for j, t in enumerate(topics):
            rows.append(
                {
                    "qid": i,
                    "year": year,
                    "subject": resolve_subject(raw_subject, t),
                    "topic": t,
                    "is_primary": j == 0 or t == primary,
                    "concept": (q.get("concept") or q.get("subtopic") or "").strip(),
                    "ask_type": q.get("ask_type") or "other",
                    "secondary_subjects": "|".join(q.get("secondary_subjects") or []),
                    "question_text": (q.get("question_text") or "")[:200],
                }
            )
    return pd.DataFrame(rows)


def score_topics(df: pd.DataFrame) -> pd.DataFrame:
    """Frequency + recurrence + recency → importance score."""
    years = sorted(df["year"].dropna().unique())
    n_years = max(len(years), 1)
    latest = max(years) if years else 2025
    # recency weights: newer years count more
    year_w = {y: 0.6 + 0.4 * ((y - min(years)) / max(latest - min(years), 1)) for y in years}

    rows = []
    for topic, g in df.groupby("topic"):
        years_seen = sorted(g["year"].dropna().unique())
        freq = g["qid"].nunique()
        weighted = sum(year_w.get(y, 1.0) * g[g["year"] == y]["qid"].nunique() for y in years_seen)
        recurrence = len(years_seen) / n_years
        # recent share
        recent_years = [y for y in years if y >= latest - 1]
        recent = g[g["year"].isin(recent_years)]["qid"].nunique()
        recent_share = recent / max(freq, 1)
        # gap since last seen (rotation signal)
        last = max(years_seen) if years_seen else latest
        gap = latest - last
        due = 1.0 if gap >= 2 and recurrence >= 0.4 else (0.5 if gap == 1 and recurrence >= 0.5 else 0.0)

        # composite 0-100
        score = (
            35 * min(freq / 20.0, 1.0)
            + 30 * recurrence
            + 20 * min(weighted / 15.0, 1.0)
            + 10 * recent_share
            + 5 * due
        )
        score = round(100 * score / 100.0, 1)
        if score >= 70:
            band = "Must"
        elif score >= 45:
            band = "High"
        elif score >= 25:
            band = "Medium"
        else:
            band = "Low"

        subjects = g["subject"].value_counts()
        # Prefer a real subject over Unknown when both appear
        real = [s for s in subjects.index if str(s).lower() not in FAKE_SUBJECTS]
        primary_subject = real[0] if real else (subjects.index[0] if len(subjects) else "Unknown")
        if primary_subject.lower() in FAKE_SUBJECTS and topic in TOPIC_SUBJECT:
            primary_subject = TOPIC_SUBJECT[topic]
        rows.append(
            {
                "topic": topic,
                "primary_subject": primary_subject,
                "question_count": freq,
                "years_seen": len(years_seen),
                "year_list": ",".join(str(int(y)) for y in years_seen),
                "recurrence": round(recurrence, 3),
                "recent_count": recent,
                "years_since_last": int(gap),
                "due_for_return": due > 0,
                "importance_score": score,
                "priority_band": band,
            }
        )
    out = pd.DataFrame(rows).sort_values(
        ["importance_score", "question_count"], ascending=False
    )
    return out.reset_index(drop=True)


def concept_stats(df: pd.DataFrame) -> pd.DataFrame:
    g = (
        df[df["concept"].astype(str).str.len() > 0]
        .groupby(["topic", "concept"])
        .agg(count=("qid", "nunique"), years=("year", lambda s: ",".join(str(int(x)) for x in sorted(set(s)))))
        .reset_index()
        .sort_values(["topic", "count"], ascending=[True, False])
    )
    return g


def ask_type_stats(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["topic", "ask_type"])
        .agg(count=("qid", "nunique"))
        .reset_index()
        .sort_values(["topic", "count"], ascending=[True, False])
    )


def overlap_stats(qs: list[dict]) -> pd.DataFrame:
    pairs = Counter()
    for q in qs:
        topics = [t for t in (q.get("topics") or []) if is_real_topic(str(t))]
        primary = q.get("topic_clean")
        if is_real_topic(primary) and primary not in topics:
            topics = [primary] + topics
        topics = sorted(set(topics))
        for i in range(len(topics)):
            for j in range(i + 1, len(topics)):
                pairs[(topics[i], topics[j])] += 1
        secs = q.get("secondary_subjects") or []
        subj = q.get("subject_clean")
        for s in secs:
            if s and subj and s != subj:
                pairs[(f"SUBJ:{subj}", f"SUBJ:{s}")] += 1
    rows = [
        {"item_a": a, "item_b": b, "co_occurrence": c}
        for (a, b), c in pairs.most_common()
    ]
    return pd.DataFrame(rows)


def next_exam_brief(importance: pd.DataFrame, concepts: pd.DataFrame) -> dict:
    must = importance[importance["priority_band"] == "Must"].head(25)
    high = importance[importance["priority_band"] == "High"].head(30)
    due = importance[importance["due_for_return"]].head(20)
    evergreen = importance[importance["years_seen"] >= 3].head(25)

    within = {}
    for topic in list(must["topic"].head(15)) + list(high["topic"].head(10)):
        top_c = concepts[concepts["topic"] == topic].head(5)
        within[topic] = [
            {"concept": r["concept"], "count": int(r["count"])} for _, r in top_c.iterrows()
        ]

    return {
        "disclaimer": (
            "Priority forecast from past-paper frequency/recurrence/recency — "
            "not a guarantee of next-exam questions. Memory-based sources only."
        ),
        "must_study_topics": must.to_dict(orient="records"),
        "high_priority_topics": high.to_dict(orient="records"),
        "due_for_return": due.to_dict(orient="records"),
        "evergreen_topics": evergreen.to_dict(orient="records"),
        "within_topic_concepts": within,
    }


def write_markdown(brief: dict, path: Path):
    lines = [
        "# NEET PG — Next Exam Priority Brief",
        "",
        f"> {brief['disclaimer']}",
        "",
        "## Must-study topics",
        "",
        "| Topic | Subject | Score | Count | Years |",
        "|-------|---------|------:|------:|-------|",
    ]
    for r in brief["must_study_topics"]:
        lines.append(
            f"| {r['topic']} | {r['primary_subject']} | {r['importance_score']} | "
            f"{r['question_count']} | {r['year_list']} |"
        )
    lines += ["", "## High priority", ""]
    for r in brief["high_priority_topics"][:20]:
        lines.append(
            f"- **{r['topic']}** ({r['primary_subject']}) — score {r['importance_score']}, "
            f"n={r['question_count']}, years={r['year_list']}"
        )
    lines += ["", "## Possibly due for return (quiet recently, strong earlier)", ""]
    if brief["due_for_return"]:
        for r in brief["due_for_return"]:
            lines.append(
                f"- {r['topic']} — last gap {r['years_since_last']}y, prior years {r['year_list']}"
            )
    else:
        lines.append("- (none flagged with current gaps)")
    lines += ["", "## Within-topic: what is actually asked", ""]
    for topic, concepts in brief["within_topic_concepts"].items():
        if not concepts:
            continue
        lines.append(f"### {topic}")
        for c in concepts:
            lines.append(f"- {c['concept']} (n={c['count']})")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def make_plots(importance: pd.DataFrame, df: pd.DataFrame, concepts: pd.DataFrame):
    PLOTS.mkdir(parents=True, exist_ok=True)
    sns.set_style("whitegrid")

    # Importance bar
    top = importance.head(25)
    fig, ax = plt.subplots(figsize=(10, 9))
    colors = {
        "Must": "#c0392b",
        "High": "#e67e22",
        "Medium": "#2980b9",
        "Low": "#95a5a6",
    }
    ax.barh(
        top["topic"][::-1],
        top["importance_score"][::-1],
        color=[colors.get(b, "#888") for b in top["priority_band"][::-1]],
    )
    ax.set_xlabel("Importance score")
    ax.set_title("Topic importance (frequency × recurrence × recency)")
    plt.tight_layout()
    fig.savefig(PLOTS / "topic_importance.png", dpi=150, bbox_inches="tight")
    plt.close()

    # Recurrence heatmap year x topic (top 20)
    tops = importance.head(20)["topic"].tolist()
    hm = (
        df[df["topic"].isin(tops)]
        .groupby(["year", "topic"])["qid"]
        .nunique()
        .unstack(fill_value=0)
    )
    hm = hm.reindex(columns=[t for t in tops if t in hm.columns])
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(hm.T, annot=True, fmt="d", cmap="YlOrRd", ax=ax)
    ax.set_title("Year × topic recurrence (top importance topics)")
    plt.tight_layout()
    fig.savefig(PLOTS / "topic_recurrence_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()

    # Concept bars for top 4 topics — short labels, more space
    top4 = importance.head(4)["topic"].tolist()
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    axes = axes.flatten()
    for ax, topic in zip(axes, top4):
        sub = concepts[concepts["topic"] == topic].head(5).copy()
        if sub.empty:
            ax.set_title(topic[:36])
            ax.text(0.5, 0.5, "No concepts yet", ha="center", transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            continue
        labels = [
            (c[:42] + "…") if len(str(c)) > 42 else str(c) for c in sub["concept"]
        ]
        ax.barh(labels[::-1], sub["count"][::-1].tolist(), color="#2c3e50")
        ax.set_title(str(topic)[:40], fontsize=11, fontweight="bold")
        ax.tick_params(axis="y", labelsize=8)
    plt.suptitle("Within-topic concepts (top 4 Must topics)", fontweight="bold", fontsize=13)
    plt.tight_layout()
    fig.savefig(PLOTS / "within_topic_concepts.png", dpi=160, bbox_inches="tight")
    plt.close()


def maybe_llm_narrative(brief: dict) -> str:
    """Optional short narrative via LLM if keys present."""
    try:
        import re
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from llm_client import available_providers, call_llm

        if not available_providers():
            return ""
        must = [r["topic"] for r in brief["must_study_topics"][:12]]
        due = [r["topic"] for r in brief["due_for_return"][:8]]
        prompt = f"""You help NEET PG aspirants prioritize revision.
Must-study topics: {must}
Possibly due for return: {due}
Write 8-12 plain bullet points (each starting with "- ").
Practical revision strategy only. No exact questions. No preamble. No thinking."""
        raw = call_llm(prompt, max_tokens=800, temperature=0.3)
        # Drop reasoning wrappers / keep bullets only
        for tag in ("</think>", "</thinking>"):
            if tag in raw:
                raw = raw.split(tag)[-1]
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip().startswith("-")]
        if len(lines) < 5:
            # fallback: keep non-empty short lines
            lines = [
                ln.strip()
                for ln in raw.splitlines()
                if ln.strip() and not ln.strip().lower().startswith("<")
            ][:12]
            lines = [ln if ln.startswith("-") else f"- {ln}" for ln in lines]
        return "\n".join(lines)
    except Exception as e:
        return f"(LLM narrative skipped: {e})"


def main():
    PLOTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    qs = load_questions()
    df = expand_topic_rows(qs)
    print(f"Questions: {len(qs)}; topic-rows (with overlaps): {len(df)}")
    if df.empty:
        print("No real topics found — run classify_llm.py first.")
        return

    importance = score_topics(df)
    concepts = concept_stats(df)
    asks = ask_type_stats(df)
    overlaps = overlap_stats(qs)
    brief = next_exam_brief(importance, concepts)

    importance.to_csv(PLOTS / "topic_importance.csv", index=False)
    concepts.to_csv(PLOTS / "concept_frequency.csv", index=False)
    asks.to_csv(PLOTS / "ask_type_by_topic.csv", index=False)
    overlaps.to_csv(PLOTS / "multi_topic_overlaps.csv", index=False)
    with open(REPORTS / "next_exam_priorities.json", "w") as f:
        json.dump(brief, f, indent=2, ensure_ascii=False)
    write_markdown(brief, REPORTS / "next_exam_priorities.md")

    make_plots(importance, df, concepts)

    narrative = maybe_llm_narrative(brief)
    if narrative:
        with open(REPORTS / "revision_strategy.txt", "w") as f:
            f.write(narrative)
        print("Wrote LLM revision strategy")

    print("Bands:", importance["priority_band"].value_counts().to_dict())
    print("Top 10:")
    print(importance.head(10)[["topic", "importance_score", "priority_band", "question_count"]])
    print(f"Reports → {REPORTS}/")
    print(f"Plots   → {PLOTS}/")


if __name__ == "__main__":
    main()
