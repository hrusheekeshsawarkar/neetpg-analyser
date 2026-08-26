#!/usr/bin/env python3
"""Clean subject names and merge all question datasets."""

import json, re
from pathlib import Path
from collections import Counter


# Subject normalization map (fix OCR/parsing errors)
SUBJECT_MAP = {
    "Anatomy": "Anatomy",
    "Physiology": "Physiology",
    "Biochemistry": "Biochemistry",
    "Biochemistry d": "Biochemistry",
    "Biochemistry a": "Biochemistry",
    "Briochemistry": "Biochemistry",
    "Pathology": "Pathology",
    "Pharmacology": "Pharmacology",
    "Prharmacology": "Pharmacology",
    "Pharmacology a": "Pharmacology",
    "Microbiology": "Microbiology",
    "Microbiology a": "Microbiology",
    "Microbiology d": "Microbiology",
    "Forensic Medicine": "Forensic Medicine",
    "Forensic Medicine d": "Forensic Medicine",
    "Community Medicine": "Community Medicine",
    "PSM": "Community Medicine",
    "SPM": "Community Medicine",
    "General Medicine": "General Medicine",
    "Mredicine": "General Medicine",
    "Mediciene": "General Medicine",
    "Medicine": "General Medicine",
    "Dermatology": "Dermatology",
    "Venereology": "Dermatology",
    "Psychiatry": "Psychiatry",
    "Psychiatry d": "Psychiatry",
    "General Surgery": "General Surgery",
    "surgery": "General Surgery",
    "Surgery": "General Surgery",
    "Surgery d": "General Surgery",
    "Surgery p": "General Surgery",
    "Orthopaedics": "Orthopaedics",
    "Anaesthesia": "Anaesthesia",
    "Anaesthesia L": "Anaesthesia",
    "Radiology": "Radiology",
    "Radiology d": "Radiology",
    "Radio-diagnosis": "Radiology",
    "Obstetrics": "Obstetrics",
    "Gynaecology": "Gynaecology",
    "Gynaecology & Obstetrics": "Obstetrics & Gynaecology",
    "Gynaecology & ObstetrLics": "Obstetrics & Gynaecology",
    "Paediatrics": "Paediatrics",
    "Pediatrics": "Paediatrics",
    "ENT": "ENT",
    "Ophthalmology": "Ophthalmology",
    "Emergency Medicine": "Emergency Medicine",
    "Chest Medicine": "Chest Medicine",
    "TB & Chest": "Chest Medicine",
    "Mixed": "Unknown",
    "Unknown": "Unknown",
}

TOPIC_MAP = {
    # Standardize common topic names
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
    "Pediatrics": "Paediatrics",
    "Orthopaedics": "Orthopaedics",
    "Anatomy": "Anatomy",
    "Physiology": "Physiology",
    "Biochemistry": "Biochemistry",
    "Pathology": "Pathology",
    "Pharmacology": "Pharmacology",
    "Microbiology": "Microbiology",
    "Surgery": "General Surgery",
    "ENT": "ENT",
    "Ophthalmology": "Ophthalmology",
    "Radiology": "Radiology",
    "Forensic": "Forensic Medicine",
    "Forensic Medicine": "Forensic Medicine",
    "SPM": "Community Medicine",
    "Community Medicine": "Community Medicine",
    "PSM": "Community Medicine",
    "Anaesthesia": "Anaesthesia",
    "Immunology": "Immunology",
    "Genetics": "Genetics",
    "Embryology": "Embryology",
    "Microanatomy": "Microanatomy",
    "Histology": "Histology",
    "Upper Limb": "Upper Limb",
    "Lower Limb": "Lower Limb",
    "Thorax": "Thorax",
    "Abdomen": "Abdomen",
    "Head & Neck": "Head & Neck",
    "CNS": "Neurology",
    "RS": "Pulmonology",
    "CVS": "Cardiology",
    "GIS": "Gastroenterology",
    "GIS / Abdomen": "Gastroenterology",
    "Reproductive": "Reproductive",
    "Infection": "Infectious Disease",
    "Infectious": "Infectious Disease",
}


def clean_subject(s: str) -> str:
    if not s:
        return "Unknown"
    s = s.strip()
    return SUBJECT_MAP.get(s, s.title() if len(s) > 2 else "Unknown")


def clean_topic(t: str) -> str:
    if not t:
        return "General"
    t = t.strip()
    if t.lower() in ["unknown", "", "na", "n/a"]:
        return "General"
    return TOPIC_MAP.get(t, t.title() if len(t) > 2 else "General")


def load_json(path: str) -> list:
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return []


def main():
    all_qs = []

    # 2021-2023 data
    for q in load_json("analysis/data/questions.json"):
        q["subject_clean"] = clean_subject(q.get("subject", ""))
        q["topic_clean"] = clean_topic(q.get("topic", ""))
        all_qs.append(q)

    # 2024 shift 1
    for q in load_json("analysis/data/q_2024_shift1.json"):
        q["subject_clean"] = clean_subject(q.get("subject", ""))
        q["topic_clean"] = clean_topic(q.get("topic", ""))
        all_qs.append(q)

    # 2024 shift 2
    for q in load_json("analysis/data/q_2024_shift2.json"):
        q["subject_clean"] = clean_subject(q.get("subject", ""))
        q["topic_clean"] = clean_topic(q.get("topic", ""))
        all_qs.append(q)

    # 2025
    for q in load_json("analysis/data/q_2025.json"):
        q["subject_clean"] = clean_subject(q.get("subject", ""))
        q["topic_clean"] = clean_topic(q.get("topic", ""))
        all_qs.append(q)

    # dedup
    seen = set()
    unique = []
    for q in all_qs:
        key = (
            q.get("year"),
            q.get("subject_clean", ""),
            q.get("question_text", "")[:100],
        )
        if key not in seen and q.get("question_text"):
            seen.add(key)
            unique.append(q)

    print(f"Total questions: {len(all_qs)}, Unique: {len(unique)}")

    # stats
    subj_counts = Counter(q["subject_clean"] for q in unique)
    print("\nSubject distribution:")
    for s, c in sorted(subj_counts.items(), key=lambda x: -x[1])[:20]:
        print(f"  {s}: {c}")

    year_counts = Counter(q["year"] for q in unique)
    print("\nYear distribution:")
    for y, c in sorted(year_counts.items()):
        print(f"  {y}: {c}")

    with open("analysis/data/merged_questions.json", "w") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(unique)} questions to analysis/data/merged_questions.json")


if __name__ == "__main__":
    main()
