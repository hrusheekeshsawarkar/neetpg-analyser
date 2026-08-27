#!/usr/bin/env python3
"""
Bulk-extract NEET PG questions from local PDFs.

Targets:
  - CollegeDunia neetpg-2010..2020 (+ 2022)
  - neetfmgeplans per-year PDFs + yearwise compilation (question sections only)

Outputs:
  analysis/data/q_collegedunia_bulk.json
  analysis/data/q_fmgeplans_bulk.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber

SUBJECTS_RE = re.compile(
    r"\b(Anatomy|Physiology|Biochemistry|Pathology|Pharmacology|Microbiology|"
    r"Forensic Medicine|Community Medicine|SPM|PSM|General Medicine|Medicine|"
    r"General Surgery|Surgery|Orthopaedics|Obstetrics|Gynaecology|Gynecology|OBG|"
    r"Paediatrics|Pediatrics|ENT|Ophthalmology|Psychiatry|Dermatology|Radiology|"
    r"Anaesthesia|Anesthesia|Radio-diagnosis|Chest Medicine)\b",
    re.I,
)


def pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        parts = []
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    text = "\n".join(parts)
    # strip page footers / headers noise
    text = re.sub(r"Page\s+\d+\s+of\s+\d+", " ", text, flags=re.I)
    text = re.sub(r"Detailed step-by-step solutions", " ", text, flags=re.I)
    return text


def parse_options(block: str) -> tuple[list[str], str]:
    """Return (4 options, question_text_without_options)."""
    opts = []
    # (A) style
    found = re.findall(r"\(([A-Da-d1-4])\)\s*([^\n(]{2,200})", block)
    if len(found) >= 2:
        opt_map = {}
        for lab, val in found:
            key = lab.upper()
            if key in "ABCD":
                opt_map[key] = val.strip()
            elif key in "1234":
                opt_map["ABCD"[int(key) - 1]] = val.strip()
        opts = [opt_map.get(c, "") for c in "ABCD"]
        # question = text before first option
        m = re.search(r"\([A-Da-d1-4]\)", block)
        q_text = block[: m.start()].strip() if m else block.strip()
        return opts, q_text

    return ["", "", "", ""], block.strip()


def parse_collegedunia(text: str, year: int, source: str) -> list[dict]:
    """Parse numbered MCQ blocks with (A)-(D) or (1)-(4) options."""
    # Drop instruction preamble (before first numbered question)
    start = re.search(r"(?m)^\s*1[\.\)]\s+", text)
    if start:
        text = text[start.start() :]

    # Split on question numbers at line start
    parts = re.split(r"(?m)^\s*(\d{1,3})[\.\)]\s+", text)
    qs = []
    for i in range(1, len(parts), 2):
        num = parts[i]
        block = parts[i + 1] if i + 1 < len(parts) else ""
        if len(block) < 15:
            continue
        opts, q_text = parse_options(block)
        q_text = re.sub(r"\s+", " ", q_text).strip()
        # skip garbage / section headers
        if len(q_text) < 20:
            continue
        if re.match(r"(?i)(general instructions|time allowed|maximum marks)", q_text):
            continue
        subj = ""
        sm = SUBJECTS_RE.search(q_text)
        if sm:
            subj = sm.group(1).title()
        qs.append(
            {
                "question_number": num,
                "year": year,
                "exam": "NEET PG" if year >= 2013 else "AIPGMEE",
                "source": source,
                "subject": subj or "Mixed",
                "topic": "",
                "subtopic": "",
                "question_text": q_text[:600],
                "option_1": opts[0],
                "option_2": opts[1],
                "option_3": opts[2],
                "option_4": opts[3],
                "answer": "",
            }
        )
    return qs


def parse_collegedunia_2022_style(text: str, year: int, source: str) -> list[dict]:
    """2022 PDF uses '1 Question' without dot and (1)-(4) options."""
    parts = re.split(r"(?m)^\s*(\d{1,3})\s+(?=[A-Z(])", text)
    qs = []
    for i in range(1, len(parts), 2):
        num = parts[i]
        block = parts[i + 1] if i + 1 < len(parts) else ""
        if len(block) < 15:
            continue
        opts, q_text = parse_options(block)
        q_text = re.sub(r"\s+", " ", q_text).strip()
        if len(q_text) < 20:
            continue
        qs.append(
            {
                "question_number": num,
                "year": year,
                "exam": "NEET PG",
                "source": source,
                "subject": "Mixed",
                "topic": "",
                "subtopic": "",
                "question_text": q_text[:600],
                "option_1": opts[0],
                "option_2": opts[1],
                "option_3": opts[2],
                "option_4": opts[3],
                "answer": "",
            }
        )
    return qs


def parse_fmge_subject_format(text: str, year: int, source: str) -> list[dict]:
    """neetfmgeplans per-year PDFs: Subject / Topic / Q.n. / options / Correct Answer."""
    qs = []
    current_subject = ""
    current_topic = ""
    chunks = re.split(r"(?m)(?:^|\n)(Q\.?\s*\d+\.|Topic:\s*)", text)
    # simpler: find Q.n. blocks
    for m in re.finditer(
        r"(?ms)(?:Topic:\s*([^\n]+)\n)?Q\.?\s*(\d+)\.\s*(.*?)(?=Topic:|Q\.?\s*\d+\.|Correct Answer:|$)",
        text,
    ):
        topic_hint = (m.group(1) or current_topic or "").strip()
        if m.group(1):
            current_topic = m.group(1).strip()
        q_num = m.group(2)
        body = m.group(3)
        # subject lines often precede topic
        subj_m = re.search(
            r"(?m)^(Anatomy|Physiology|Biochemistry|Pathology|Pharmacology|Microbiology|"
            r"Forensic Medicine|Community Medicine|General Medicine|General Surgery|"
            r"Orthopaedics|Obstetrics|Gynaecology|Paediatrics|ENT|Ophthalmology|Psychiatry|"
            r"Dermatology|Radiology|Anaesthesia)\s*$",
            text[: m.start()],
        )
        if subj_m:
            current_subject = subj_m.group(1)
        opts = re.findall(r"(?m)^\s*([1-4])\.\s*([^\n]+)", body)
        q_lines = []
        for ln in body.split("\n"):
            if re.match(r"^\s*[1-4]\.\s+", ln):
                break
            if re.match(r"(?i)correct answer", ln):
                break
            q_lines.append(ln.strip())
        q_text = " ".join(x for x in q_lines if x)
        q_text = re.sub(r"\s+", " ", q_text).strip()
        if len(q_text) < 15:
            continue
        clean_opts = ["", "", "", ""]
        for lab, val in opts[:4]:
            idx = int(lab) - 1
            if 0 <= idx < 4:
                clean_opts[idx] = val.strip()
        ans_m = re.search(r"(?i)Correct Answer:\s*([^\n]+)", body)
        qs.append(
            {
                "question_number": q_num,
                "year": year,
                "exam": "NEET PG",
                "source": source,
                "subject": current_subject or "Mixed",
                "topic": topic_hint,
                "subtopic": "",
                "question_text": q_text[:600],
                "option_1": clean_opts[0],
                "option_2": clean_opts[1],
                "option_3": clean_opts[2],
                "option_4": clean_opts[3],
                "answer": ans_m.group(1).strip() if ans_m else "",
            }
        )
    return qs


def parse_fmge_yearwise(text: str, source: str) -> list[dict]:
    """Extract from MEDINK yearwise book — question sections only."""
    qs = []
    # Split into year sections by EXAMINATION PAPER YYYY (not SOLUTION)
    sections = re.split(
        r"(?m)EXAMINATION PAPER\s+(20\d{2})(?!.*SOLUTION)", text
    )
    years_found = re.findall(r"(?m)EXAMINATION PAPER\s+(20\d{2})(?!.*SOLUTION)", text)
    for year_str, section in zip(years_found, sections[1:]):
        year = int(year_str)
        # stop at solutions section
        section = re.split(r"(?m)EXAMINATION PAPER.*SOLUTION|SOLUTIONS", section)[0]
        year_qs = parse_collegedunia(section, year, source)
        if len(year_qs) < 30:
            # fallback: numbered questions with (A)-(D) anywhere in section
            year_qs = parse_collegedunia(section, year, source)
        qs.extend(year_qs)
    return qs


def dedup_questions(qs: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for q in qs:
        key = (q.get("year"), q.get("question_text", "")[:100].lower())
        if key in seen or not q.get("question_text"):
            continue
        seen.add(key)
        out.append(q)
    return out


def extract_collegedunia_bulk() -> list[dict]:
    cd_dir = Path("neet-pg-papers/collegedunia")
    years = list(range(2010, 2021)) + [2022]
    all_qs = []
    for year in years:
        path = cd_dir / f"neetpg-{year}.pdf"
        if not path.exists():
            print(f"  skip missing {path.name}")
            continue
        print(f"  {path.name}...", end=" ", flush=True)
        text = pdf_text(path)
        if year == 2022:
            qs = parse_collegedunia_2022_style(text, year, "collegedunia")
        else:
            qs = parse_collegedunia(text, year, "collegedunia")
        print(len(qs))
        all_qs.extend(qs)
    return dedup_questions(all_qs)


def extract_fmgeplans_bulk() -> list[dict]:
    base = Path("neet-pg-papers/neetfmgeplans")
    all_qs = []

    # Per-year smaller PDFs
    for path in sorted(base.glob("NEETPG-20*.pdf")):
        year_m = re.search(r"(20\d{2})", path.name)
        if not year_m:
            continue
        year = int(year_m.group(1))
        if path.stat().st_size > 30_000_000:
            print(f"  skip huge {path.name}")
            continue
        print(f"  {path.name}...", end=" ", flush=True)
        text = pdf_text(path)
        qs = parse_fmge_subject_format(text, year, "neetfmgeplans")
        if len(qs) < 5:
            qs = parse_collegedunia(text, year, "neetfmgeplans")
        print(len(qs))
        all_qs.extend(qs)

    # Yearwise compilation (758 pages — question sections)
    yw = base / "NEETPG-yearwise.pdf"
    if yw.exists():
        print(f"  NEETPG-yearwise.pdf (this may take a minute)...", end=" ", flush=True)
        text = pdf_text(yw)
        # Only keep pages/regions that look like exam papers (not solution pages)
        # Remove solution-heavy regions
        text = re.sub(
            r"(?ms)EXAMINATION PAPER\s+20\d{2}\s+SOLUTION.*?(?=EXAMINATION PAPER\s+20\d{2}(?!.*SOLUTION)|$)",
            "\n",
            text,
        )
        yw_qs = parse_fmge_yearwise(text, "neetfmgeplans-yearwise")
        print(len(yw_qs))
        all_qs.extend(yw_qs)

    return dedup_questions(all_qs)


def main():
    out_cd = Path("analysis/data/q_collegedunia_bulk.json")
    out_fm = Path("analysis/data/q_fmgeplans_bulk.json")

    print("=== CollegeDunia 2010-2020 + 2022 ===")
    cd_qs = extract_collegedunia_bulk()
    out_cd.write_text(json.dumps(cd_qs, indent=2, ensure_ascii=False))
    print(f"Saved {len(cd_qs)} → {out_cd}")

    from collections import Counter

    print("Years:", dict(sorted(Counter(q["year"] for q in cd_qs).items())))

    print("\n=== neetfmgeplans ===")
    fm_qs = extract_fmgeplans_bulk()
    out_fm.write_text(json.dumps(fm_qs, indent=2, ensure_ascii=False))
    print(f"Saved {len(fm_qs)} → {out_fm}")
    print("Years:", dict(sorted(Counter(q["year"] for q in fm_qs).items())))


if __name__ == "__main__":
    main()
