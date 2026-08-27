#!/usr/bin/env python3
"""Extract additional NEET PG 2024 questions from CollegeDunia PDF (Shift 1 heavy)."""

import json
import re
from pathlib import Path

import pdfplumber

OUT = Path("analysis/data/q_2024_collegedunia.json")
PDF = Path("neet-pg-papers/collegedunia/neetpg-2024.pdf")


def main():
    with pdfplumber.open(PDF) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    # CollegeDunia: numbered questions often as "1." or "Q.1"
    blocks = re.split(r"(?:^|\n)\s*(?:Q\.?\s*)?(\d{1,3})[\.\)]\s+", text)
    qs = []
    for i in range(1, len(blocks), 2):
        num = blocks[i]
        content = blocks[i + 1] if i + 1 < len(blocks) else ""
        # skip TOC-ish short noise
        if len(content) < 40:
            continue
        opts = re.findall(
            r"(?:^|\n)\s*\(?([A-Da-d1-4])\)?[\.\)]\s*([^\n]{3,120})", content
        )
        lines = []
        for ln in content.split("\n"):
            if re.match(r"\s*\(?[A-Da-d1-4]\)?[\.\)]\s+", ln):
                break
            if re.match(r"(?i)\s*(ans|solution|explanation)\b", ln):
                break
            lines.append(ln.strip())
        q_text = " ".join(x for x in lines if x)[:500]
        if len(q_text) < 25:
            continue
        # Map options
        clean_opts = []
        for lab, val in opts[:4]:
            clean_opts.append(val.strip())
        qs.append(
            {
                "question_number": num,
                "year": 2024,
                "exam": "NEET PG",
                "shift": "1",
                "source": "collegedunia",
                "subject": "Mixed",
                "topic": "",
                "subtopic": "",
                "question_text": q_text,
                "option_1": clean_opts[0] if len(clean_opts) > 0 else "",
                "option_2": clean_opts[1] if len(clean_opts) > 1 else "",
                "option_3": clean_opts[2] if len(clean_opts) > 2 else "",
                "option_4": clean_opts[3] if len(clean_opts) > 3 else "",
                "answer": "",
            }
        )

    # Dedup by question text prefix
    seen = set()
    unique = []
    for q in qs:
        key = q["question_text"][:90].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(q)

    OUT.write_text(json.dumps(unique, indent=2, ensure_ascii=False))
    print(f"Saved {len(unique)} questions → {OUT}")


if __name__ == "__main__":
    main()
