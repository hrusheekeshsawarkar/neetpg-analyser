#!/usr/bin/env python3
"""Parse NEET PG 2024-2025 Nishant Bhushan format (simple numbered)."""

import os, pdfplumber, json, re, urllib.request
from pathlib import Path

LLM_API = "https://llmapi-key.ris.bht-berlin.de/v1/chat/completions"
LLM_KEY = os.environ["BHT_LLM_KEY"]
MODEL = "bht/large"


def call_llm(prompt: str, max_tokens: int = 4000) -> str:
    payload = json.dumps(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.05,
        }
    ).encode()
    req = urllib.request.Request(
        LLM_API,
        data=payload,
        headers={"Content-Type": "application/json", "x-api-key": LLM_KEY},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]


def extract_pdf_text(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        parts = []
        for i, page in enumerate(pdf.pages):
            t = page.extract_text()
            if t and len(t.strip()) > 15:
                parts.append(t)
        return "\n".join(parts)


def parse_ques_dot_format(text: str) -> list:
    """Parse 'Ques 1. ... Ans. B' format (Nishant 2024 shift 1)."""
    questions = []
    blocks = re.split(r"(?:^|\n)(?:Ques\.?\s*)(\d+)\.\s*", text)

    for i in range(1, len(blocks), 2):
        try:
            q_num = blocks[i]
            content = blocks[i + 1] if i + 1 < len(blocks) else ""

            # Extract answer
            ans_m = re.search(r"(?:^|\n)\s*Ans\.?\s*([A-D])", content)
            if not ans_m:
                ans_m = re.search(r"Ans\.?\s*(\d+)", content)

            # Extract options
            opts = re.findall(r"\n([A-D])\.\s*([^\n]+)", content)

            # Question text is first sentence/line
            lines = content.strip().split("\n")
            q_text_lines = []
            for ln in lines:
                if re.match(r"[A-D]\.", ln):
                    break
                q_text_lines.append(ln)
            q_text = " ".join(q_text_lines).strip()

            # Map letter answer to number
            ans_map = {"A": "1", "B": "2", "C": "3", "D": "4"}
            answer = ""
            if ans_m:
                letter = ans_m.group(1)
                answer = ans_map.get(letter, ans_m.group(1))

            if q_text and len(q_text) > 10:
                q = {
                    "question_number": q_num,
                    "year": 2024,
                    "exam": "NEET PG",
                    "subject": "Mixed",
                    "topic": "Unknown",
                    "subtopic": "",
                    "question_text": q_text,
                    "option_1": opts[0][1].strip() if len(opts) > 0 else "",
                    "option_2": opts[1][1].strip() if len(opts) > 1 else "",
                    "option_3": opts[2][1].strip() if len(opts) > 2 else "",
                    "option_4": opts[3][1].strip() if len(opts) > 3 else "",
                    "answer": answer,
                }
                questions.append(q)
        except Exception:
            pass

    return questions


def parse_pgmasters_format(text: str) -> list:
    """Parse PG Masters table format (Nishant 2025)."""
    questions = []

    # Table has: Q.No | Topic/Subject | Question/Answer/Scenario
    # Example: '1 Parasitology Image-based Enterobius...'
    lines = text.split("\n")

    current_q = {}
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue

        # Match: number at start + topic + question
        m = re.match(r"^(\d+)\s+([A-Za-z\s/]+?)\s+(.+)$", line)
        if m:
            if current_q.get("question_text"):
                questions.append(current_q)

            q_num = m.group(1)
            topic_subj = m.group(2).strip()
            rest = m.group(3).strip()

            # Parse topic/subject
            parts = topic_subj.split("/")
            subject = parts[0].strip() if parts else "Unknown"
            topic = parts[1].strip() if len(parts) > 1 else ""

            current_q = {
                "question_number": q_num,
                "year": 2025,
                "exam": "NEET PG",
                "subject": subject,
                "topic": topic,
                "subtopic": "",
                "question_text": rest[:200],
                "answer": "",
            }

    if current_q.get("question_text"):
        questions.append(current_q)

    return questions


def llm_extract(text_chunk: str, year: int, exam: str, subject: str = "Mixed") -> list:
    """Use LLM to extract questions, handling model output quirks."""
    prompt = f"""Extract questions from the following NEET PG paper text (year {year}).

Return ONLY valid JSON array (no markdown, no explanation, no thinking). Each object must have:
- question_number: string
- subject: one of Anatomy, Physiology, Biochemistry, Pathology, Pharmacology, Microbiology, Forensic Medicine, Community Medicine, General Medicine, Dermatology, Psychiatry, General Surgery, Orthopaedics, Anaesthesia, Obstetrics, Gynaecology, Paediatrics, ENT, Ophthalmology, Radiology, Emergency Medicine, Chest Medicine
- topic: string (specific topic within subject)
- question_text: the full question
- option_1 through option_4: the four options
- answer: the number 1-4 of the correct answer

If options not in text, leave as empty string.

TEXT:
{text_chunk[:6000]}

JSON array:"""

    try:
        response = call_llm(prompt)

        # Find JSON boundaries - look for [ at start or after any non-JSON
        json_text = ""

        # Try: content is array directly
        if response.strip().startswith("["):
            idx = response.rfind("]") + 1
            json_text = response[:idx]
        else:
            # Look for array start/end anywhere
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                json_text = response[start:end]

        if json_text:
            parsed = json.loads(json_text)
            for q in parsed:
                q["year"] = year
                q["exam"] = exam
            return parsed
    except Exception as e:
        print(f"    LLM parse error: {e}")

    return []


def main():
    nb_dir = Path("neet-pg-papers/nishant-bhushan")

    # 2024 Shift 1
    f2024s1 = nb_dir / "NEETPG-2024-shift1.pdf"
    if f2024s1.exists():
        print("=== NEETPG-2024-shift1.pdf ===")
        text = extract_pdf_text(str(f2024s1))
        print(f"  Text length: {len(text)}")

        qs = parse_ques_dot_format(text)
        print(f"  Parsed {len(qs)} questions from Ques. format")

        if len(qs) < 30:
            print("  Trying LLM extraction...")
            qs2 = llm_extract(text, 2024, "NEET PG")
            print(f"  LLM extracted {len(qs2)}")
            qs = qs or qs2

        # Save
        with open("analysis/data/q_2024_shift1.json", "w") as f:
            json.dump(qs, f, indent=2)

    # 2024 Shift 2 (memory-based recall PDF is short; prefer regex first)
    f2024s2 = nb_dir / "NEETPG-2024-shift2.pdf"
    if f2024s2.exists():
        print("\n=== NEETPG-2024-shift2.pdf ===")
        text = extract_pdf_text(str(f2024s2))
        print(f"  Text length: {len(text)}")

        qs = parse_ques_dot_format(text)
        for q in qs:
            q["shift"] = "2"
        print(f"  Parsed {len(qs)} questions from Ques. format")

        if len(qs) < 20:
            print("  Trying LLM extraction...")
            qs2 = llm_extract(text, 2024, "NEET PG")
            print(f"  LLM extracted {len(qs2)}")
            qs = qs2 if len(qs2) > len(qs) else qs
            for q in qs:
                q.setdefault("shift", "2")

        with open("analysis/data/q_2024_shift2.json", "w") as f:
            json.dump(qs, f, indent=2, ensure_ascii=False)

    # 2025
    f2025 = nb_dir / "NEETPG-2025.pdf"
    if f2025.exists():
        print("\n=== NEETPG-2025.pdf ===")
        text = extract_pdf_text(str(f2025))
        print(f"  Text length: {len(text)}")

        qs = parse_pgmasters_format(text)
        print(f"  PG Masters format: {len(qs)} questions")

        qs2 = llm_extract(text, 2025, "NEET PG")
        print(f"  LLM: {len(qs2)} questions")

        qs = qs2 if len(qs2) > len(qs) else qs

        with open("analysis/data/q_2025.json", "w") as f:
            json.dump(qs, f, indent=2)

    print("\nDone!")


if __name__ == "__main__":
    main()
