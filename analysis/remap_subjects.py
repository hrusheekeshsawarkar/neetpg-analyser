#!/usr/bin/env python3
"""Remap subject_clean / subject to taught MBBS subjects; fill Unknown from topic."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from mbbs_taxonomy import MBBS_SUBJECTS, normalize_subject, topic_to_subject_map

DATA = Path("analysis/data/merged_questions.json")
CHECKPOINT = Path("analysis/data/llm_classify_checkpoint.json")


def remap_question(q: dict, topic_subj: dict[str, str]) -> dict:
    raw = q.get("subject_clean") or q.get("subject") or ""
    subj = normalize_subject(raw)
    if subj == "Unknown":
        topic = (q.get("topic_clean") or q.get("topic") or "").strip()
        if topic in topic_subj:
            subj = topic_subj[topic]
        else:
            for t in q.get("topics") or []:
                if t in topic_subj:
                    subj = topic_subj[t]
                    break
    q["subject_clean"] = subj
    q["subject"] = subj
    # secondary subjects
    secs = []
    for s in q.get("secondary_subjects") or []:
        ns = normalize_subject(s)
        if ns in MBBS_SUBJECTS and ns != subj:
            secs.append(ns)
    q["secondary_subjects"] = secs
    return q


def main():
    topic_subj = topic_to_subject_map()
    with open(DATA) as f:
        qs = json.load(f)
    qs = [remap_question(q, topic_subj) for q in qs]
    with open(DATA, "w") as f:
        json.dump(qs, f, indent=2, ensure_ascii=False)
    if CHECKPOINT.exists():
        with open(CHECKPOINT, "w") as f:
            json.dump(qs, f, indent=2, ensure_ascii=False)
    counts = Counter(q["subject_clean"] for q in qs)
    print(f"Remapped {len(qs)} questions")
    for s in MBBS_SUBJECTS + ["Unknown"]:
        print(f"  {s}: {counts.get(s, 0)}")
    other = {k: v for k, v in counts.items() if k not in MBBS_SUBJECTS and k != "Unknown"}
    if other:
        print("  OTHER:", other)


if __name__ == "__main__":
    main()
