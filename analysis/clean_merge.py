#!/usr/bin/env python3
"""Clean subject names and merge all question datasets."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from mbbs_taxonomy import MBBS_SUBJECTS, normalize_subject

# Kept for reference / OCR aliases (normalize_subject is authoritative)
SUBJECT_MAP = {
    "Anatomy": "Anatomy",
    "Physiology": "Physiology",
    "Biochemistry": "Biochemistry",
    "Pathology": "Pathology",
    "Pharmacology": "Pharmacology",
    "Microbiology": "Microbiology",
    "Forensic Medicine": "Forensic Medicine",
    "Community Medicine": "Community Medicine",
    "PSM": "Community Medicine",
    "SPM": "Community Medicine",
    "General Medicine": "Medicine",
    "Medicine": "Medicine",
    "Emergency Medicine": "Medicine",
    "Dermatology": "Dermatology",
    "Psychiatry": "Psychiatry",
    "General Surgery": "Surgery",
    "Surgery": "Surgery",
    "Orthopaedics": "Orthopedics",
    "Orthopedics": "Orthopedics",
    "Anaesthesia": "Anaesthesia",
    "Anesthesia": "Anaesthesia",
    "Radiology": "Radiology",
    "Obstetrics": "OBG",
    "Gynaecology": "OBG",
    "OBG": "OBG",
    "Obstetrics & Gynaecology": "OBG",
    "Paediatrics": "Pediatrics",
    "Pediatrics": "Pediatrics",
    "ENT": "ENT",
    "Ophthalmology": "Ophthalmology",
    "Unknown": "Unknown",
}

TOPIC_MAP = {
    "Cardiology": "Cardiology",
    "Neurology": "Neurology",
    "Nephrology": "Nephrology",
    "Pulmonology": "Pulmonology",
    "Gastroenterology": "Gastroenterology",
    "Endocrinology": "Endocrinology",
    "Hematology": "Hematology",
    "Dermatology": "Dermatology",
    "Psychiatry": "Psychiatry",
    "Obstetrics": "Obstetrics",
    "Gynaecology": "Gynaecology",
    "Pediatrics": "Pediatrics",
    "Paediatrics": "Pediatrics",
    "Orthopaedics": "Orthopedics",
    "Orthopedics": "Orthopedics",
    "Surgery": "Surgery",
    "CNS": "Neurology",
    "RS": "Pulmonology",
    "CVS": "Cardiology",
    "GIS": "Gastroenterology",
    "Infection": "Infectious Diseases",
    "Infectious": "Infectious Diseases",
}


def clean_subject(s: str) -> str:
    if not s:
        return "Unknown"
    return normalize_subject(s.strip())


def clean_topic(t: str) -> str:
    """Normalize topic; never invent 'General' — empty means unlabeled."""
    if not t:
        return ""
    t = t.strip()
    if t.lower() in ["unknown", "", "na", "n/a", "general", "others", "mixed"]:
        return ""
    return TOPIC_MAP.get(t, t.title() if len(t) > 2 else "")


def load_json(path: str) -> list:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return []


def enrich(q: dict) -> dict:
    q = dict(q)
    raw_subj = q.get("subject_clean") or q.get("subject") or ""
    q["subject_clean"] = clean_subject(raw_subj)
    q["subject"] = q["subject_clean"]
    raw_topic = q.get("topic_clean") or q.get("topic") or ""
    if raw_topic.lower() in ("general", "unknown", "others", "mixed"):
        raw_topic = ""
    cleaned = clean_topic(raw_topic) if raw_topic else ""
    if cleaned:
        q["topic_clean"] = cleaned
        q["topic"] = cleaned
    elif not (q.get("topic_clean") or "").strip():
        q["topic_clean"] = ""
    return q


def merge_score(q: dict) -> int:
    """Prefer records with LLM labels / concepts when deduping."""
    score = 0
    if q.get("label_source") == "llm":
        score += 100
    if q.get("concept"):
        score += 50
    if q.get("topic_clean"):
        score += 20
    if q.get("topics"):
        score += 10
    if q.get("option_1"):
        score += 5
    return score


def main():
    all_qs = []

    sources = [
        "analysis/data/questions.json",
        "analysis/data/q_2024_shift1.json",
        "analysis/data/q_2024_shift2.json",
        "analysis/data/q_2025.json",
        "analysis/data/q_2024_collegedunia.json",
        "analysis/data/q_collegedunia_bulk.json",
        "analysis/data/q_fmgeplans_bulk.json",
        "analysis/data/q_aipgmee_2012_2016.json",
        "analysis/data/q_fmgeplans_2022_2023.json",
        "analysis/data/q_fmgeplans_chapterwise.json",
        "analysis/data/q_aipgmee_2017_2018.json",
        "analysis/data/q_nishant_2019_2020.json",
        "analysis/data/q_fmgeplans_2024_2025.json",
        "analysis/data/llm_classify_checkpoint.json",
        "analysis/data/merged_questions.json",
    ]

    for src in sources:
        for q in load_json(src):
            all_qs.append(enrich(q))

    # Dedup: keep richest record per (year, question text prefix)
    best: dict = {}
    for q in all_qs:
        text = (q.get("question_text") or "").strip()
        if not text:
            continue
        key = (q.get("year"), text[:120].lower())
        prev = best.get(key)
        if prev is None or merge_score(q) > merge_score(prev):
            best[key] = q

    unique = list(best.values())
    print(f"Total raw rows: {len(all_qs)}, Unique: {len(unique)}")

    subj_counts = Counter(q["subject_clean"] for q in unique)
    print("\nSubject distribution:")
    for s in MBBS_SUBJECTS + ["Unknown"]:
        print(f"  {s}: {subj_counts.get(s, 0)}")

    year_counts = Counter(q["year"] for q in unique)
    print("\nYear distribution:")
    for y, c in sorted(year_counts.items()):
        print(f"  {y}: {c}")

    out = Path("analysis/data/merged_questions.json")
    with open(out, "w") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(unique)} questions to {out}")


if __name__ == "__main__":
    main()
