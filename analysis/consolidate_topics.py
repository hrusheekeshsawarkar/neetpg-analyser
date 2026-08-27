#!/usr/bin/env python3
"""
Map free-form LLM topic strings onto curated SUBJECT_TOPICS so Pareto /
importance charts aren't flooded by one-off spellings.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from mbbs_taxonomy import SUBJECT_TOPICS, topic_to_subject_map

DATA = Path("analysis/data/merged_questions.json")
CHECKPOINT = Path("analysis/data/llm_classify_checkpoint.json")

# Explicit aliases → canonical topic
TOPIC_ALIASES = {
    "infectious disease": "Infectious Diseases",
    "infectious diseases": "Infectious Diseases",
    "infection": "Infectious Diseases",
    "cvs": "Cardiology",
    "cardiovascular": "Cardiology",
    "rs": "Pulmonology",
    "respiratory system": "Pulmonology",
    "respiratory": "Pulmonology",
    "git": "Gastroenterology",
    "gi": "Gastroenterology",
    "cns": "Neurology",
    "central nervous system": "Neurology",
    "obg": "Obstetric Complications",
    "obstetrics": "Obstetric Complications",
    "gynaecology": "Gynecologic Oncology",
    "gynecology": "Gynecologic Oncology",
    "paediatrics": "Neonatology",
    "pediatrics": "Neonatology",
    "ortho": "Fractures",
    "orthopaedics": "Fractures",
    "orthopedics": "Fractures",
    "psm": "Epidemiology",
    "spm": "Epidemiology",
    "community medicine": "Epidemiology",
    "fmt": "Thanatology",
    "forensic": "Thanatology",
    "genetics": "Genetics & Molecular Biology",
    "molecular biology": "Genetics & Molecular Biology",
    "nutrition": "Vitamins & Nutrition",
    "vitamins": "Vitamins & Nutrition",
    "vitamin deficiency": "Vitamins & Nutrition",
    "antimicrobials": "Antimicrobials",
    "antibiotics": "Antimicrobials",
    "ans": "Autonomic",
    "autonomic nervous system": "Autonomic",
    "general pharmacology": "General Pharmacology",
    "cell injury": "Cell Injury & Death",
    "inflammation": "Inflammation & Healing",
    "healing": "Inflammation & Healing",
    "neoplasia": "Neoplasia",
    "tumor": "Neoplasia",
    "tumour": "Neoplasia",
    "hematology": "Hematopathology",
    "haematology": "Hematopathology",
    "blood": "Hematopathology",
    "ear": "Ear",
    "nose": "Nose & PNS",
    "throat": "Throat & Larynx",
    "cornea": "Cornea & Refractive",
    "cataract": "Lens & Cataract",
    "lens": "Lens & Cataract",
    "retina": "Retina",
    "glaucoma": "Glaucoma",
    "xray": "X-ray",
    "x-ray": "X-ray",
    "ct": "CT",
    "mri": "MRI",
    "usg": "Ultrasound",
    "ultrasound": "Ultrasound",
    "fracture": "Fractures",
    "fractures": "Fractures",
    "spine": "Spine",
    "joint": "Joints & Arthritis",
    "joints": "Joints & Arthritis",
    "neonatology": "Neonatology",
    "growth": "Growth & Development",
    "development": "Growth & Development",
    "labor": "Labor & Delivery",
    "labour": "Labor & Delivery",
    "pregnancy": "Antenatal Care",
    "antenatal": "Antenatal Care",
    "contraception": "Contraception",
    "infertility": "Infertility",
    "schizophrenia": "Schizophrenia & Psychosis",
    "depression": "Mood Disorders",
    "bipolar": "Mood Disorders",
    "anxiety": "Anxiety & OCD",
    "leprosy": "Leprosy",
    "std": "STDs",
    "sti": "STDs",
    "urology": "Urology",
    "hernia": "Hernia & Abdominal Wall",
    "breast": "Breast & Endocrine Surgery",
    "thyroid surgery": "Breast & Endocrine Surgery",
    "trauma": "Trauma",
    "burns": "Burns & Plastic",
}


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def build_canonical_index() -> dict[str, str]:
    """lowercase / alias → canonical topic label."""
    idx = {}
    for topics in SUBJECT_TOPICS.values():
        for t in topics:
            idx[_norm(t)] = t
            # also without punctuation
            idx[re.sub(r"[^a-z0-9 ]", "", _norm(t))] = t
    for alias, canon in TOPIC_ALIASES.items():
        idx[_norm(alias)] = canon
    return idx


def consolidate_topic(raw: str, idx: dict[str, str]) -> str:
    if not raw or raw.lower() in ("general", "unknown", "others", "mixed", ""):
        return ""
    key = _norm(raw)
    if key in idx:
        return idx[key]
    key2 = re.sub(r"[^a-z0-9 ]", "", key)
    if key2 in idx:
        return idx[key2]
    # substring / containment against curated topics (longest match)
    best = ""
    best_len = 0
    for k, canon in idx.items():
        if len(k) < 4:
            continue
        if k in key or key in k:
            if len(k) > best_len:
                best, best_len = canon, len(k)
    if best:
        return best
    # Title-case keep (still unique but cleaner)
    return raw.strip()


def main():
    idx = build_canonical_index()
    topic_subj = topic_to_subject_map()
    with open(DATA) as f:
        qs = json.load(f)

    before = Counter(
        (q.get("topic_clean") or "").strip()
        for q in qs
        if (q.get("topic_clean") or "").strip()
    )
    changed = 0
    for q in qs:
        old = (q.get("topic_clean") or q.get("topic") or "").strip()
        new = consolidate_topic(old, idx)
        if new != old:
            changed += 1
        if new:
            q["topic_clean"] = new
            q["topic"] = new
            topics = q.get("topics") or []
            if isinstance(topics, list):
                q["topics"] = [consolidate_topic(t, idx) or t for t in topics][:3]
                q["topics"] = [t for t in q["topics"] if t]
            else:
                q["topics"] = [new]
            # if subject unknown, fill from topic
            if (q.get("subject_clean") or "").lower() in ("", "unknown"):
                subj = topic_subj.get(new)
                if subj:
                    q["subject_clean"] = subj
                    q["subject"] = subj

    after = Counter(
        (q.get("topic_clean") or "").strip()
        for q in qs
        if (q.get("topic_clean") or "").strip()
    )
    with open(DATA, "w") as f:
        json.dump(qs, f, indent=2, ensure_ascii=False)
    with open(CHECKPOINT, "w") as f:
        json.dump(qs, f, indent=2, ensure_ascii=False)

    print(f"Topics before: {len(before)} → after: {len(after)} (rows changed: {changed})")
    tot = sum(after.values())
    cum = 0
    n80 = 0
    for i, (_, n) in enumerate(after.most_common(), 1):
        cum += n
        if cum / tot >= 0.8:
            n80 = i
            break
    print(f"80% coverage at {n80} topics (of {len(after)})")
    print("Top 15:", after.most_common(15))


if __name__ == "__main__":
    main()
