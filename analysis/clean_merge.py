#!/usr/bin/env python3
"""Clean subject names and merge all question datasets."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from mbbs_taxonomy import MBBS_SUBJECTS, normalize_subject

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).resolve().parent / "data"

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


def load_json(path: Path | str) -> list:
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
    """Prefer records with LLM labels / concepts / answers when deduping."""
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
    if q.get("answer"):
        score += 40
    if q.get("answer_note"):
        score += 25
    return score


def _fill_missing(dst: dict, src: dict) -> dict:
    """Union complementary fields so answers/explanations from any source stick."""
    out = dict(dst)
    for k in (
        "answer",
        "answer_note",
        "option_1",
        "option_2",
        "option_3",
        "option_4",
        "subject",
        "subject_clean",
        "topic",
        "topic_clean",
        "concept",
        "ask_type",
        "label_source",
        "shift",
        "source",
    ):
        cur = out.get(k)
        new = src.get(k)
        if (cur is None or cur == "") and new not in (None, ""):
            out[k] = new
    # Prefer longer explanation
    if src.get("answer_note") and len(str(src.get("answer_note") or "")) > len(
        str(out.get("answer_note") or "")
    ):
        out["answer_note"] = src["answer_note"]
    return out


def main():
    all_qs = []

    sources = [
        DATA / "questions.json",
        DATA / "q_2024_shift1.json",
        DATA / "q_2024_shift2.json",
        DATA / "q_2025.json",
        DATA / "q_2024_collegedunia.json",
        DATA / "q_collegedunia_bulk.json",
        DATA / "q_fmgeplans_bulk.json",
        DATA / "q_aipgmee_2012_2016.json",
        DATA / "q_fmgeplans_2022_2023.json",
        DATA / "q_fmgeplans_chapterwise.json",
        DATA / "q_aipgmee_2017_2018.json",
        DATA / "q_nishant_2019_2020.json",
        DATA / "q_fmgeplans_2024_2025.json",
        DATA / "q_firstranker.json",
        DATA / "llm_classify_checkpoint.json",
        DATA / "merged_questions.json",
    ]

    for src in sources:
        for q in load_json(src):
            all_qs.append(enrich(q))

    # Dedup: keep richest record per (year, question text prefix),
    # then fill missing answer / explanation / options from siblings.
    best: dict = {}
    siblings: dict = {}
    for q in all_qs:
        text = (q.get("question_text") or "").strip()
        if not text:
            continue
        key = (q.get("year"), text[:120].lower())
        siblings.setdefault(key, []).append(q)
        prev = best.get(key)
        if prev is None or merge_score(q) > merge_score(prev):
            best[key] = q

    unique = []
    filled_ans = filled_note = 0
    for key, winner in best.items():
        merged = winner
        before_ans = bool(merged.get("answer"))
        before_note = bool(merged.get("answer_note"))
        for other in siblings.get(key, []):
            if other is winner:
                continue
            merged = _fill_missing(merged, other)
        if not before_ans and merged.get("answer"):
            filled_ans += 1
        if not before_note and merged.get("answer_note"):
            filled_note += 1
        unique.append(merged)

    # Cross-year answer propagation: same stem in another year often carries
    # the key/explanation (FirstRanker banks are not clean single-year papers).
    by_stem: dict[str, dict] = {}
    for q in unique:
        stem = (q.get("question_text") or "").strip()[:120].lower()
        if not stem:
            continue
        if q.get("answer") or q.get("answer_note"):
            prev = by_stem.get(stem)
            if prev is None or merge_score(q) > merge_score(prev):
                by_stem[stem] = q
    cross_ans = cross_note = 0
    for q in unique:
        stem = (q.get("question_text") or "").strip()[:120].lower()
        donor = by_stem.get(stem)
        if not donor or donor is q:
            continue
        before_ans = bool(q.get("answer"))
        before_note = bool(q.get("answer_note"))
        filled = _fill_missing(q, donor)
        q.clear()
        q.update(filled)
        if not before_ans and q.get("answer"):
            cross_ans += 1
        if not before_note and q.get("answer_note"):
            cross_note += 1

    print(f"Total raw rows: {len(all_qs)}, Unique: {len(unique)}")
    print(f"Union fills — answers: {filled_ans}, explanations: {filled_note}")
    print(f"Cross-year fills — answers: {cross_ans}, explanations: {cross_note}")

    subj_counts = Counter(q["subject_clean"] for q in unique)
    print("\nSubject distribution:")
    for s in MBBS_SUBJECTS + ["Unknown"]:
        print(f"  {s}: {subj_counts.get(s, 0)}")

    year_counts = Counter(q["year"] for q in unique)
    print("\nYear distribution:")
    for y, c in sorted(year_counts.items()):
        print(f"  {y}: {c}")

    out = DATA / "merged_questions.json"
    with open(out, "w") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(unique)} questions to {out}")
    ans_n = sum(1 for q in unique if q.get("answer"))
    note_n = sum(1 for q in unique if q.get("answer_note"))
    print(f"With answer: {ans_n} ({100*ans_n/max(1,len(unique)):.1f}%)")
    print(f"With explanation: {note_n} ({100*note_n/max(1,len(unique)):.1f}%)")


if __name__ == "__main__":
    main()
