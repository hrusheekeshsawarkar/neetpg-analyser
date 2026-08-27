#!/usr/bin/env python3
"""Generate one revision pack markdown per taught MBBS subject."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from mbbs_taxonomy import MBBS_SUBJECTS, SUBJECT_TOPICS
from predict_priority import expand_topic_rows, is_real_topic, score_topics

DATA = Path("analysis/data/merged_questions.json")
OUT = Path("analysis/reports/subjects")
INDEX = Path("analysis/reports/subject_revision_packs.md")


def main():
    qs = json.load(open(DATA))
    df = expand_topic_rows(qs)
    importance = score_topics(df) if len(df) else pd.DataFrame()

    OUT.mkdir(parents=True, exist_ok=True)
    index_lines = [
        "# Subject-wise revision packs",
        "",
        "Must / High topics from past-paper frequency × recurrence × recency.",
        "",
        "| Subject | Questions | Must topics | Pack |",
        "|---------|----------:|------------:|------|",
    ]

    for subj in MBBS_SUBJECTS:
        sub_qs = [q for q in qs if (q.get("subject_clean") or "") == subj]
        n = len(sub_qs)
        # topics for this subject
        if len(importance):
            # importance is global; filter rows whose primary_subject matches
            sub_imp = importance[importance["primary_subject"] == subj].copy()
            if sub_imp.empty:
                # fallback: topics appearing under this subject in expand rows
                tcounts = (
                    df[df["subject"] == subj]
                    .groupby("topic")["qid"]
                    .nunique()
                    .sort_values(ascending=False)
                )
                must = []
                high = [(t, int(c)) for t, c in tcounts.head(15).items()]
            else:
                must = sub_imp[sub_imp["priority_band"] == "Must"].head(12)
                high = sub_imp[sub_imp["priority_band"] == "High"].head(15)
        else:
            must, high = [], []

        # concepts
        concepts = Counter()
        ask = Counter()
        for q in sub_qs:
            c = (q.get("concept") or "").strip()
            if c:
                concepts[c] += 1
            a = (q.get("ask_type") or "other").strip()
            ask[a] += 1

        years = sorted({q.get("year") for q in sub_qs if q.get("year")})
        syllabus = SUBJECT_TOPICS.get(subj, [])

        lines = [
            f"# {subj} — Revision pack",
            "",
            f"> {n} questions · years {years[0] if years else '?'}–{years[-1] if years else '?'}",
            "",
            "## Syllabus map (study under these headings)",
            "",
        ]
        for t in syllabus:
            lines.append(f"- {t}")
        lines += ["", "## Must-study topics", ""]
        if isinstance(must, pd.DataFrame) and len(must):
            lines += [
                "| Topic | Score | Count | Years |",
                "|-------|------:|------:|-------|",
            ]
            for _, r in must.iterrows():
                lines.append(
                    f"| {r['topic']} | {r['importance_score']} | {r['question_count']} | {r['year_list']} |"
                )
            must_n = len(must)
        elif high and isinstance(high, list):
            lines.append("_No Must band yet — top by frequency:_")
            for t, c in high[:10]:
                lines.append(f"- **{t}** ({c})")
            must_n = 0
        else:
            lines.append("_Insufficient labeled topics._")
            must_n = 0

        lines += ["", "## High priority", ""]
        if isinstance(high, pd.DataFrame) and len(high):
            for _, r in high.iterrows():
                lines.append(
                    f"- **{r['topic']}** — score {r['importance_score']}, n={r['question_count']}"
                )
        elif isinstance(high, list):
            for t, c in high[10:]:
                lines.append(f"- **{t}** ({c})")
        else:
            lines.append("_—_")

        lines += ["", "## Top concepts asked", ""]
        for c, n_c in concepts.most_common(15):
            lines.append(f"- {c} ({n_c})")
        if not concepts:
            lines.append("_No concept tags yet._")

        lines += ["", "## Ask-type mix", ""]
        for a, n_a in ask.most_common():
            lines.append(f"- {a}: {n_a}")

        path = OUT / f"{subj.lower().replace(' ', '_')}.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        index_lines.append(
            f"| {subj} | {n} | {must_n} | [{path.name}](subjects/{path.name}) |"
        )
        print(f"Wrote {path} ({n} qs)")

    INDEX.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"Index → {INDEX}")


if __name__ == "__main__":
    main()
