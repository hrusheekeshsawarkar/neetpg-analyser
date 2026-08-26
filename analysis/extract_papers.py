#!/usr/bin/env python3
"""
Extract structured questions from NEET PG PDFs.
Prioritizes Nishant Bhushan format (clean structured extraction).
"""

import pdfplumber
import re
import json
import os
from pathlib import Path


def extract_nishant_format(pdf_path: str, year: int, exam: str = "NEET PG"):
    """Extract from Nishant Bhushan structured format PDFs."""
    questions = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
    except Exception as e:
        print(f"  Error opening {pdf_path}: {e}")
        return []

    # Pattern: Subject: X -> Topic: Y -> Sub-Topic: Z -> Question -> Options -> Ans
    # Let's chunk by "Ques No:" markers
    blocks = re.split(r"(Ques\s*No[:\s]+\d+)", full_text)

    i = 1
    while i < len(blocks):
        marker = blocks[i]
        content = blocks[i + 1] if i + 1 < len(blocks) else ""

        q = {}
        q["question_number"] = (
            re.search(r"(\d+)", marker).group(1) if re.search(r"(\d+)", marker) else ""
        )
        q["year"] = year
        q["exam"] = exam

        # Extract subject
        subj_match = re.search(r"Subject[:\s]+([A-Za-z\s/]+?)(?=\n|Topic)", content)
        if subj_match:
            q["subject"] = subj_match.group(1).strip()
        else:
            q["subject"] = "Unknown"

        # Extract topic
        topic_match = re.search(
            r"Topic[:\s]+([A-Za-z\s/\-]+?)(?=\n|Sub-Topic)", content
        )
        if topic_match:
            q["topic"] = topic_match.group(1).strip()
        else:
            q["topic"] = "Unknown"

        # Extract sub-topic
        st_match = re.search(
            r"Sub-Topic[:\s]*([^\n]*?)(?=\n[^O]|\nO[1-4]|Ans:)", content
        )
        if st_match:
            q["subtopic"] = st_match.group(1).strip()
        else:
            q["subtopic"] = ""

        # Extract question text (between subtopic/end markers and O1)
        q_text_match = re.search(
            r"(?:Sub-Topic[:\s]*[^\n]*\n)(.*?)(?=\nO\s*1[:\s]|\nO1[:\s]|\nO 1[:\s])",
            content,
            re.DOTALL,
        )
        if q_text_match:
            q["question_text"] = q_text_match.group(1).strip()
        else:
            # Fallback: get text before O1
            o1_match = re.search(r"(.*?)\nO\s*1[:\s]", content, re.DOTALL)
            if o1_match:
                q["question_text"] = o1_match.group(1).strip()
            else:
                q["question_text"] = content[:200].strip()

        # Extract options
        for opt in [1, 2, 3, 4]:
            opts = re.findall(rf"O\s*{opt}\s*[:\s]+([^\n]+)", content)
            if opts:
                q[f"option_{opt}"] = opts[0].strip()
            else:
                q[f"option_{opt}"] = ""

        # Extract answer
        ans_match = re.search(r"Ans[:\s]+(\d+)", content)
        if ans_match:
            q["answer"] = ans_match.group(1)

        # Skip garbage
        if q.get("subject") and q["subject"] != "Unknown":
            questions.append(q)

        i += 2

    return questions


def extract_collegedunia_format(pdf_path: str, year: int):
    """Extract from CollegeDunia format PDFs."""
    questions = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
    except Exception as e:
        print(f"  Error: {e}")
        return []

    # Pattern: numbered questions at start of line (1., 2., etc.)
    # Look for subject markers
    lines = full_text.split("\n")

    current_q = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for question number at start
        q_match = re.match(r"^(\d+)\s+(?:\d+\.\s+)?(.+)", line)
        if q_match:
            # Save previous
            if current_q.get("question_text"):
                questions.append(current_q)

            q_num = q_match.group(1)
            rest = q_match.group(2)
            current_q = {
                "question_number": q_num,
                "year": year,
                "exam": "NEET PG",
                "question_text": rest,
                "subject": "Unknown",
                "topic": "Unknown",
                "subtopic": "",
            }

            # Check if this line contains subject
            subj_match = re.search(
                r"\b(Anatomy|Physiology|Biochemistry|Pathology|Pharmacology|Microbiology|Forensic Medicine|Community Medicine|SPM|General Medicine|General Surgery|Orthopaedics|Obstetrics|Gynaecology|OBG|Paediatrics|Pediatrics|ENT|Ophthalmology|Psychiatry|Dermatology|Radiology|Anaesthesia|Radio-diagnosis)\b",
                rest,
                re.I,
            )
            if subj_match:
                current_q["subject"] = subj_match.group(1).title()

    if current_q.get("question_text"):
        questions.append(current_q)

    return questions


def extract_neetfmgeplans_yearwise(pdf_path: str):
    """Extract from neetfmgeplans yearwise compilation."""
    questions = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Only process first 200 pages for efficiency
            for page_num, page in enumerate(pdf.pages[:200]):
                t = page.extract_text()
                if not t or len(t.strip()) < 30:
                    continue

                # Look for year markers
                year_matches = re.findall(
                    r"(?:NEET\s*PG|NEETPG|AIPGMEE)[-\s]*(20\d{2}|19\d{2})", t, re.I
                )
                if not year_matches:
                    continue

                year = int(year_matches[0])

                # Try to extract subject/topic
                subj_match = re.search(r"Subject[:\s]+([A-Za-z\s/]+)", t)
                topic_match = re.search(r"Topic[:\s]+([A-Za-z\s/]+)", t)

                q_num_match = re.search(r"Q\.?\s*No[:\s]*(\d+)", t, re.I)

                if q_num_match:
                    q = {
                        "question_number": q_num_match.group(1),
                        "year": year,
                        "exam": "NEET PG" if year >= 2019 else "AIPGMEE",
                        "subject": subj_match.group(1).strip()
                        if subj_match
                        else "Unknown",
                        "topic": topic_match.group(1).strip()
                        if topic_match
                        else "Unknown",
                        "subtopic": "",
                        "question_text": t[:300].strip(),
                    }
                    questions.append(q)
    except Exception as e:
        print(f"  Error: {e}")

    return questions


def main():
    base_dir = Path("neet-pg-papers")
    all_questions = []

    # Nishant Bhushan PDFs (best format)
    nb_dir = base_dir / "nishant-bhushan"
    nb_files = {
        "AIPGMEE-2017.pdf": (2017, "AIPGMEE"),
        "AIPGMEE-2018.pdf": (2018, "AIPGMEE"),
        "NEETPG-2019.pdf": (2019, "NEET PG"),
        "NEETPG-2020.pdf": (2020, "NEET PG"),
        "NEETPG-2021.pdf": (2021, "NEET PG"),
        "NEETPG-2022.pdf": (2022, "NEET PG"),
        "NEETPG-2023.pdf": (2023, "NEET PG"),
        "NEETPG-2024-shift1.pdf": (2024, "NEET PG"),
        "NEETPG-2024-shift2.pdf": (2024, "NEET PG"),
        "NEETPG-2025.pdf": (2025, "NEET PG"),
    }

    print("=== Extracting Nishant Bhushan PDFs ===")
    for fname, (year, exam) in nb_files.items():
        fpath = nb_dir / fname
        if fpath.exists():
            print(f"  Processing {fname}...")
            qs = extract_nishant_format(str(fpath), year, exam)
            print(f"    -> {len(qs)} questions extracted")
            all_questions.extend(qs)

    # CollegeDunia PDFs
    cd_dir = base_dir / "collegedunia"
    cd_files = {
        "neetpg-2010.pdf": 2010,
        "neetpg-2011.pdf": 2011,
        "neetpg-2012.pdf": 2012,
        "neetpg-2013.pdf": 2013,
        "neetpg-2014.pdf": 2014,
        "neetpg-2015.pdf": 2015,  # skip duplicate
        "neetpg-2016.pdf": 2016,
        "neetpg-2017.pdf": 2017,
        "neetpg-2018.pdf": 2018,
        "neetpg-2019.pdf": 2019,
        "neetpg-2020.pdf": 2020,
        "neetpg-2021.pdf": 2021,
        "neetpg-2022.pdf": 2022,
        "neetpg-2023.pdf": 2023,
        "neetpg-2024.pdf": 2024,
        "neetpg-2025.pdf": 2025,
    }

    print("\n=== Extracting CollegeDunia PDFs ===")
    for fname, year in cd_files.items():
        fpath = cd_dir / fname
        if fpath.exists():
            print(f"  Processing {fname}...")
            qs = extract_collegedunia_format(str(fpath), year)
            print(f"    -> {len(qs)} questions extracted")
            all_questions.extend(qs)

    # neetfmgeplans yearwise
    print("\n=== Extracting neetfmgeplans yearwise ===")
    yw_path = base_dir / "neetfmgeplans" / "NEETPG-yearwise.pdf"
    if yw_path.exists():
        qs = extract_neetfmgeplans_yearwise(str(yw_path))
        print(f"  -> {len(qs)} questions extracted")
        all_questions.extend(qs)

    # Save
    out_path = "analysis/data/raw_questions.json"
    with open(out_path, "w") as f:
        json.dump(all_questions, f, indent=2)

    print(f"\n=== Total: {len(all_questions)} questions extracted ===")

    # Deduplicate by (year, subject, question_number)
    seen = set()
    unique = []
    for q in all_questions:
        key = (q.get("year"), q.get("subject"), q.get("question_number", ""))
        if key not in seen:
            seen.add(key)
            unique.append(q)

    print(f"=== Unique: {len(unique)} questions after dedup ===")

    with open("analysis/data/unique_questions.json", "w") as f:
        json.dump(unique, f, indent=2)

    return unique


if __name__ == "__main__":
    main()
