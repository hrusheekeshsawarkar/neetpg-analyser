#!/usr/bin/env python3
"""
Extract questions from NEET PG PDFs using the LLM API.
Sends text chunks to LLM for structured extraction.
"""

import pdfplumber
import json
import os
import time
import re
from pathlib import Path

LLM_API = "https://llmapi-key.ris.bht-berlin.de/v1/chat/completions"
LLM_KEY = os.environ["BHT_LLM_KEY"]
MODEL = "bht/large"

SUBJECTS = [
    "Anatomy",
    "Physiology",
    "Biochemistry",
    "Pathology",
    "Pharmacology",
    "Microbiology",
    "Forensic Medicine",
    "Community Medicine",
    "SPM",
    "General Medicine",
    "Dermatology",
    "Psychiatry",
    "Venereology",
    "General Surgery",
    "Orthopaedics",
    "Anaesthesia",
    "Radiology",
    "Obstetrics",
    "Gynaecology",
    "Paediatrics",
    "ENT",
    "Ophthalmology",
    "Radiodiagnosis",
    "Emergency Medicine",
    "Chest Medicine",
    "TB & Chest",
    "Medicine",
    "Surgery",
]

SUBJECT_PATTERN = "|".join(SUBJECTS)


def call_llm(prompt: str, max_tokens: int = 4000) -> str:
    """Call LLM API with prompt, return response text."""
    import urllib.request

    payload = json.dumps(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
    ).encode()

    req = urllib.request.Request(
        LLM_API,
        data=payload,
        headers={"Content-Type": "application/json", "x-api-key": LLM_KEY},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  LLM API error: {e}")
        return ""


def extract_text_from_pdf(pdf_path: str, max_pages: int = None) -> str:
    """Extract text from all pages of a PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            pages_to_read = min(total, max_pages) if max_pages else total
            texts = []
            for i in range(pages_to_read):
                t = pdf.pages[i].extract_text()
                if t and len(t.strip()) > 20:
                    texts.append(f"[PAGE {i + 1}]\n{t}")
            return "\n\n".join(texts)
    except Exception as e:
        print(f"  PDF error: {e}")
        return ""


def parse_nishant_format(text: str, year: int, exam: str) -> list:
    """Parse clean Nishant Bhushan structured format."""
    questions = []

    blocks = re.split(r"(?:Ques\s*No|Q\.?\s*No|Question\s*No)[:\s]*(\d+)", text)

    i = 1
    while i < len(blocks):
        try:
            q_num = blocks[i]
            content = blocks[i + 1]

            subj_m = re.search(r"(?:^|\n)Subject[:\s]*([^\n]+)", content)
            topic_m = re.search(r"(?:^|\n)Topic[:\s]*([^\n]+)", content)
            st_m = re.search(r"(?:^|\n)Sub-Topic[:\s]*([^\n]*)", content)

            o1_m = re.search(r"O\s*1[:\s]*([^\n]+)", content)
            o2_m = re.search(r"O\s*2[:\s]*([^\n]+)", content)
            o3_m = re.search(r"O\s*3[:\s]*([^\n]+)", content)
            o4_m = re.search(r"O\s*4[:\s]*([^\n]+)", content)
            ans_m = re.search(r"Ans[:\s]*(\d+)", content)

            q_text_m = re.search(
                r"(?:Sub-Topic[:\s]*[^\n]*\n)(.*?)(?=\n\s*O\s*1)", content, re.DOTALL
            )

            subject = subj_m.group(1).strip() if subj_m else "Unknown"

            q = {
                "question_number": q_num.strip(),
                "year": year,
                "exam": exam,
                "subject": subject,
                "topic": topic_m.group(1).strip() if topic_m else "Unknown",
                "subtopic": st_m.group(1).strip() if st_m else "",
                "question_text": q_text_m.group(1).strip()
                if q_text_m
                else content[:200].strip(),
                "option_1": o1_m.group(1).strip() if o1_m else "",
                "option_2": o2_m.group(1).strip() if o2_m else "",
                "option_3": o3_m.group(1).strip() if o3_m else "",
                "option_4": o4_m.group(1).strip() if o4_m else "",
                "answer": ans_m.group(1) if ans_m else "",
            }

            if subject != "Unknown" and q["question_text"]:
                questions.append(q)
        except Exception:
            pass

        i += 2

    return questions


def parse_medical_junction_format(text: str, year: int, exam: str) -> list:
    """Parse Medical-Junction.com format (Nishant 2021)."""
    questions = []

    lines = text.split("\n")
    current_subject = "Unknown"
    current_q = {}
    q_num = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        stripped = line.strip()

        subj_m = re.search(
            r"\b(Anatomy|Physiology|Biochemistry|Pathology|Pharmacology|"
            r"Microbiology|Forensic Medicine|Community Medicine|SPM|"
            r"General Medicine|Dermatology|Psychiatry|Venereology|"
            r"General Surgery|Orthopaedics|Anaesthesia|Radiology|"
            r"Obstetrics|Gynaecology|Paediatrics|ENT|Ophthalmology|"
            r"Radiodiagnosis|Emergency Medicine|Chest Medicine|Medicine|Surgery|"
            r"TB & Chest|Radio-diagnosis)\b",
            stripped,
            re.I,
        )

        if subj_m and len(stripped) < 30:
            current_subject = subj_m.group(1)
            continue

        num_match = re.match(r"^(\d+)\.\s*(.+)", stripped)
        if num_match:
            if current_q and current_q.get("question_text"):
                current_q["subject"] = current_subject
                questions.append(current_q)

            q_num += 1
            current_q = {
                "question_number": num_match.group(1),
                "year": year,
                "exam": exam,
                "subject": current_subject,
                "topic": "Unknown",
                "subtopic": "",
                "question_text": num_match.group(2),
            }

            ans_m = re.search(r"Answer:\s*[A-D]?\s*(.+)$", stripped)
            if ans_m:
                current_q["answer_note"] = ans_m.group(1)

            continue

        opt_m = re.match(r"^[A-D]\.\s*(.+)", stripped)
        if opt_m and current_q:
            key = f"option_{len([k for k in current_q if k.startswith('option_')]) + 1}"
            current_q[key] = opt_m.group(1)
            continue

        ans_match = re.search(r"Answer:\s*([^\n]+)", stripped)
        if ans_match and current_q:
            current_q["answer_note"] = ans_match.group(1).strip()

    if current_q and current_q.get("question_text"):
        questions.append(current_q)

    return questions


def llm_extract(text_chunk: str, year: int, exam: str) -> list:
    """Use LLM to extract structured questions from raw text."""
    prompt = f"""You are a medical exam question parser. Extract structured questions from the NEET PG paper text below.

Return a JSON array. Each object has: question_number, year, exam, subject, topic, subtopic, question_text, option_1 through option_4, answer (1-4).

Rules:
- If a field is not found, use empty string or "Unknown"
- Subject must be one of: Anatomy, Physiology, Biochemistry, Pathology, Pharmacology, Microbiology, Forensic Medicine, Community Medicine, General Medicine, Dermatology, Psychiatry, General Surgery, Orthopaedics, Anaesthesia, Obstetrics, Gynaecology, Paediatrics, ENT, Ophthalmology, Radiology, Radio-diagnosis, Emergency Medicine, Chest Medicine
- Topics within subjects: e.g., Cardiology within General Medicine, Abdomen within Anatomy, etc.
- answer field: the number (1-4) of the correct option

Extract ALL questions from the text. Be thorough.

TEXT:
{text_chunk[:8000]}

JSON output (valid JSON array only, no markdown):"""

    response = call_llm(prompt)

    if not response:
        return []

    try:
        json_start = response.find("[")
        json_end = response.rfind("]") + 1
        if json_start >= 0 and json_end > json_start:
            parsed = json.loads(response[json_start:json_end])
            for q in parsed:
                q["year"] = year
                q["exam"] = exam
            return parsed
    except Exception as e:
        print(f"  JSON parse error: {e}")

    return []


def main():
    base_dir = Path("neet-pg-papers")
    all_questions = []

    # Priority 1: Nishant Bhushan 2022-2023 (cleanest format)
    nb_dir = base_dir / "nishant-bhushan"

    nb_files = {
        "NEETPG-2022.pdf": (2022, "NEET PG"),
        "NEETPG-2023.pdf": (2023, "NEET PG"),
    }

    print("=== Nishant Bhushan 2022-2023 (structured parser) ===")
    for fname, (year, exam) in nb_files.items():
        fpath = nb_dir / fname
        if not fpath.exists():
            continue

        print(f"  Extracting {fname}...")
        text = extract_text_from_pdf(str(fpath), max_pages=120)
        qs = parse_nishant_format(text, year, exam)
        print(f"    -> {len(qs)} questions")
        all_questions.extend(qs)

    # Priority 2: Nishant Bhushan 2021 (medical-junction format)
    nb_2021 = nb_dir / "NEETPG-2021.pdf"
    if nb_2021.exists():
        print(f"\n=== Nishant Bhushan 2021 (medical-junction parser) ===")
        text = extract_text_from_pdf(str(nb_2021), max_pages=150)
        qs = parse_medical_junction_format(text, 2021, "NEET PG")
        print(f"  -> {len(qs)} questions")
        all_questions.extend(qs)

    # Priority 3: Nishant Bhushan 2024-2025 (smaller - check format)
    for fname, (year, exam) in [
        ("NEETPG-2024-shift1.pdf", (2024, "NEET PG")),
        ("NEETPG-2024-shift2.pdf", (2024, "NEET PG")),
        ("NEETPG-2025.pdf", (2025, "NEET PG")),
    ]:
        fpath = nb_dir / fname
        if not fpath.exists():
            continue

        print(f"\n=== {fname} (trying LLM) ===")
        text = extract_text_from_pdf(str(fpath))
        if text:
            qs = parse_nishant_format(text, year, exam)
            if len(qs) > 50:
                print(f"  -> {len(qs)} questions (structured parser)")
                all_questions.extend(qs)
            else:
                print(f"  -> Only {len(qs)} questions, trying LLM...")
                qs2 = llm_extract(text, year, exam)
                print(f"  -> LLM extracted {len(qs2)} questions")
                all_questions.extend(qs2)

    # Priority 4: CollegeDunia 2022 (clean numbered format)
    cd_dir = base_dir / "collegedunia"
    cd_files = {
        "neetpg-2022.pdf": 2022,
        "neetpg-2023.pdf": 2023,
    }

    print("\n=== CollegeDunia 2022-2023 (LLM extraction) ===")
    for fname, year in cd_files.items():
        fpath = cd_dir / fname
        if not fpath.exists():
            continue

        print(f"  Extracting {fname}...")
        text = extract_text_from_pdf(str(fpath), max_pages=80)
        if text:
            qs = llm_extract(text, year, "NEET PG")
            print(f"  -> {len(qs)} questions")
            all_questions.extend(qs)

    # Deduplicate
    seen = set()
    unique = []
    for q in all_questions:
        key = (
            q.get("year"),
            q.get("subject"),
            q.get("question_number", q.get("question_text", "")[:100]),
        )
        if key not in seen:
            seen.add(key)
            unique.append(q)

    print(f"\n=== Final: {len(all_questions)} total, {len(unique)} unique ===")

    with open("analysis/data/questions.json", "w") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    return unique


if __name__ == "__main__":
    main()
