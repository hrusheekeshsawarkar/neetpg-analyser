#!/usr/bin/env python3
"""
Extract remaining high-value local PDFs:

  1. Nishant AIPGMEE 2012–2016  (text: "1. Q ... a) .. Correct Answer - A")
  2. neetfmgeplans NEETPG-2022/2023  (text: Ques No / Subject / Topic — NOT vision)
  3. neetfmgeplans NEETPG-chapterwise.pdf  (text: numbered MCQs in chapter bank)

Usage:
  python3 analysis/extract_remaining.py              # all three
  python3 analysis/extract_remaining.py --aipgmee
  python3 analysis/extract_remaining.py --fmge-years
  python3 analysis/extract_remaining.py --chapterwise
  python3 analysis/extract_remaining.py --aipgmee --limit-pages 50   # smoke test

Then:
  python3 analysis/clean_merge.py
  python3 analysis/classify_topics.py
  # wait for / after Gemini job:
  python3 analysis/classify_llm.py
  python3 analysis/predict_priority.py && python3 analysis/analyze.py
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pdfplumber

OUT_DIR = Path("analysis/data")
ANS_MAP = {"A": "1", "B": "2", "C": "3", "D": "4", "a": "1", "b": "2", "c": "3", "d": "4"}


def pdf_text(path: Path, limit_pages: int = 0) -> str:
    parts = []
    with pdfplumber.open(path) as pdf:
        pages = pdf.pages[:limit_pages] if limit_pages else pdf.pages
        for page in pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    return "\n".join(parts)


def parse_aipgmee(text: str, year: int) -> list[dict]:
    """Parse '1. question ... a) .. Correct Answer - A' blocks."""
    # Split on numbered questions at line start
    parts = re.split(r"(?m)^\s*(\d+)\.\s+", text)
    qs = []
    for i in range(1, len(parts), 2):
        num = parts[i]
        block = parts[i + 1] if i + 1 < len(parts) else ""
        if len(block) < 20:
            continue
        # Stop explanation after Correct Answer / Ans.
        stop = re.search(r"(?i)Correct Answer\s*-\s*([A-Da-d])|Ans\.?\s*(?:is\s*)?['\"]?([A-Da-d])", block)
        answer = ""
        body = block
        if stop:
            answer = ANS_MAP.get((stop.group(1) or stop.group(2) or "").strip(), "")
            body = block[: stop.start()]

        opts = re.findall(r"(?m)^\s*([a-dA-D])\)\s*(.+)$", body)
        if len(opts) < 2:
            opts = re.findall(r"\b([a-dA-D])\)\s*([^a-dA-D\n]{2,120})", body)

        # question = before first option
        m = re.search(r"(?m)^\s*[a-dA-D]\)\s*", body)
        q_text = body[: m.start()].strip() if m else body.strip()
        q_text = re.sub(r"\s+", " ", q_text).strip()
        # strip trailing explanation crumbs
        if len(q_text) < 15:
            continue

        clean = ["", "", "", ""]
        for lab, val in opts[:4]:
            idx = ord(lab.upper()) - ord("A")
            if 0 <= idx < 4:
                clean[idx] = re.sub(r"\s+", " ", val).strip()[:200]

        qs.append(
            {
                "question_number": num,
                "year": year,
                "exam": "AIPGMEE",
                "source": "nishant-aipgmee",
                "subject": "Mixed",
                "topic": "",
                "subtopic": "",
                "question_text": q_text[:600],
                "option_1": clean[0],
                "option_2": clean[1],
                "option_3": clean[2],
                "option_4": clean[3],
                "answer": answer,
            }
        )
    return qs


def parse_ques_no_format(text: str, year: int, source: str) -> list[dict]:
    """Nishant / fmgeplans: Ques No: N / Subject / Topic / O1..O4 / Ans."""
    blocks = re.split(r"(?i)Ques\s*No\s*:\s*(\d+)", text)
    qs = []
    for i in range(1, len(blocks), 2):
        num = blocks[i]
        content = blocks[i + 1] if i + 1 < len(blocks) else ""
        subj_m = re.search(r"(?i)Subject\s*:\s*([^\n]+)", content)
        topic_m = re.search(r"(?i)^Topic\s*:\s*([^\n]+)", content, re.M)
        # Prefer text after Sub-Topic line; else after Topic line; strip metadata lines
        q_m = re.search(
            r"(?is)Sub-Topic\s*:\s*[^\n]*\n(.*?)(?=\nO\s*1\s*:|\nO1\s*:)",
            content,
        )
        if not q_m:
            q_m = re.search(
                r"(?is)Topic\s*:\s*[^\n]*\n(?:Sub-Topic\s*:\s*[^\n]*\n)?(.*?)(?=\nO\s*1\s*:|\nO1\s*:)",
                content,
            )
        q_text = (q_m.group(1) if q_m else "").strip()
        # remove any leftover Subject/Topic header lines
        q_text = re.sub(
            r"(?im)^\s*(Subject|Topic|Sub-Topic)\s*:.*$", "", q_text
        ).strip()
        q_text = re.sub(r"\s+", " ", q_text).strip()
        if len(q_text) < 10:
            continue
        opts = {}
        for n in (1, 2, 3, 4):
            om = re.search(rf"(?im)^\s*O\s*{n}\s*:\s*(.+)$", content)
            if om:
                opts[n] = om.group(1).strip()
        ans_m = re.search(r"(?i)Ans\s*:\s*(\d+|[A-D])", content)
        answer = ""
        if ans_m:
            a = ans_m.group(1)
            answer = ANS_MAP.get(a, a)
        subject = (subj_m.group(1).strip() if subj_m else "Mixed")
        topic = (topic_m.group(1).strip() if topic_m else "")
        qs.append(
            {
                "question_number": num,
                "year": year,
                "exam": "NEET PG",
                "source": source,
                "subject": subject,
                "topic": topic,
                "subtopic": "",
                "question_text": q_text[:600],
                "option_1": opts.get(1, ""),
                "option_2": opts.get(2, ""),
                "option_3": opts.get(3, ""),
                "option_4": opts.get(4, ""),
                "answer": answer,
            }
        )
    return qs


def parse_chapterwise(text: str) -> list[dict]:
    """Chapter bank: '52. Question ... (A) .. (B) ..' — year often in Ans : 2024."""
    parts = re.split(r"(?m)^\s*(\d+)\.\s+", text)
    qs = []
    for i in range(1, len(parts), 2):
        num = parts[i]
        block = parts[i + 1] if i + 1 < len(parts) else ""
        if len(block) < 25:
            continue
        # Prefer question stem before first (A)
        m = re.search(r"\(A\)", block)
        body = block[: m.start()] if m else block
        # Drop long explanation paragraphs (heuristic)
        q_text = re.sub(r"\s+", " ", body).strip()
        if len(q_text) < 20 or len(q_text) > 500:
            # try first 2 sentences only
            q_text = " ".join(q_text.split(". ")[:2])[:500]
        if len(q_text) < 20:
            continue

        opts = re.findall(r"\(([A-D])\)\s*([^\n(]{2,160})", block)
        clean = ["", "", "", ""]
        for lab, val in opts[:4]:
            clean[ord(lab) - ord("A")] = val.strip()[:200]

        year = None
        ym = re.search(r"Ans\s*:\s*(20\d{2})", block)
        if ym:
            year = int(ym.group(1))

        qs.append(
            {
                "question_number": num,
                "year": year or 0,  # filled later if 0
                "exam": "NEET PG",
                "source": "neetfmgeplans-chapterwise",
                "subject": "Mixed",
                "topic": "",
                "subtopic": "",
                "question_text": q_text[:600],
                "option_1": clean[0],
                "option_2": clean[1],
                "option_3": clean[2],
                "option_4": clean[3],
                "answer": "",
                "year_hint": year,
            }
        )
    # If year missing, leave 0 — clean_merge skips empty year? keep as 2018-2025 bank
    for q in qs:
        if not q["year"]:
            q["year"] = 2024  # chapter bank spans 2018-2025; tag mid for now
            q["exam"] = "NEET PG (chapterwise)"
    return qs


def dedup(qs: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for q in qs:
        key = (q.get("year"), q.get("question_text", "")[:100].lower())
        if key in seen or not q.get("question_text"):
            continue
        seen.add(key)
        out.append(q)
    return out


def parse_question_n_format(text: str, year: int, exam: str = "AIPGMEE") -> list[dict]:
    """Parse 'Question 1\\n...\\nA> ... / A) ...' blocks (AIPGMEE-2017 style)."""
    parts = re.split(r"(?im)^\s*Question\s+(\d+)\s*$", text)
    qs = []
    for i in range(1, len(parts), 2):
        block = parts[i + 1] if i + 1 < len(parts) else ""
        if len(block) < 20:
            continue
        stop = re.search(
            r"(?i)Correct Answer\s*[-:]\s*([A-Da-d])|Ans\.?\s*(?:is\s*)?['\"]?([A-Da-d])",
            block,
        )
        answer = ""
        body = block
        if stop:
            answer = ANS_MAP.get((stop.group(1) or stop.group(2) or "").strip(), "")
            body = block[: stop.start()]
        opts = re.findall(r"(?m)^\s*([A-Da-d])[\)>]\s*(.+)$", body)
        if len(opts) < 2:
            opts = re.findall(r"\b([A-Da-d])[\)>]\s*([^A-Da-d\n]{2,120})", body)
        m = re.search(r"(?m)^\s*[A-Da-d][\)>]\s*", body)
        q_text = body[: m.start()].strip() if m else body.strip()
        q_text = re.sub(r"\s+", " ", q_text).strip()
        if len(q_text) < 15:
            continue
        clean = ["", "", "", ""]
        for lab, val in opts[:4]:
            idx = ord(lab.upper()) - ord("A")
            if 0 <= idx < 4:
                clean[idx] = val.strip()[:300]
        qs.append(
            {
                "year": year,
                "exam": exam,
                "question_number": int(parts[i]),
                "question_text": q_text[:800],
                "option_1": clean[0],
                "option_2": clean[1],
                "option_3": clean[2],
                "option_4": clean[3],
                "answer": answer,
                "source": "nishant-aipgmee" if exam == "AIPGMEE" else "nishant-neetpg",
                "subject": "",
                "topic": "",
            }
        )
    return qs


def extract_aipgmee(limit_pages: int = 0, years=None) -> list[dict]:
    nb = Path("neet-pg-papers/nishant-bhushan")
    all_qs = []
    years = years or range(2012, 2017)
    for year in years:
        path = nb / f"AIPGMEE-{year}.pdf"
        if not path.exists():
            print(f"  missing {path}")
            continue
        print(f"  {path.name}...", end=" ", flush=True)
        text = pdf_text(path, limit_pages=limit_pages)
        if year == 2017:
            qs = parse_question_n_format(text, year, "AIPGMEE")
        else:
            qs = parse_aipgmee(text, year)
        print(len(qs))
        all_qs.extend(qs)
    return dedup(all_qs)


def extract_nishant_neetpg_gap(limit_pages: int = 0) -> list[dict]:
    """NEETPG 2019–2020 Nishant PDFs (same numbered format as AIPGMEE-2018)."""
    nb = Path("neet-pg-papers/nishant-bhushan")
    all_qs = []
    for year in (2019, 2020):
        path = nb / f"NEETPG-{year}.pdf"
        if not path.exists():
            print(f"  missing {path}")
            continue
        print(f"  {path.name}...", end=" ", flush=True)
        text = pdf_text(path, limit_pages=limit_pages)
        qs = parse_aipgmee(text, year)
        for q in qs:
            q["exam"] = "NEET PG"
            q["source"] = "nishant-neetpg"
        print(len(qs))
        all_qs.extend(qs)
    return dedup(all_qs)


def extract_fmge_years(limit_pages: int = 0, years=(2022, 2023)) -> list[dict]:
    base = Path("neet-pg-papers/neetfmgeplans")
    all_qs = []
    for year in years:
        path = base / f"NEETPG-{year}.pdf"
        if not path.exists():
            print(f"  missing {path}")
            continue
        print(f"  {path.name} ({path.stat().st_size // 1_000_000}MB)...", end=" ", flush=True)
        text = pdf_text(path, limit_pages=limit_pages)
        qs = parse_ques_no_format(text, year, "neetfmgeplans")
        print(len(qs))
        all_qs.extend(qs)
    return dedup(all_qs)


def extract_chapterwise(limit_pages: int = 0) -> list[dict]:
    path = Path("neet-pg-papers/neetfmgeplans/NEETPG-chapterwise.pdf")
    print(f"  {path.name}...", end=" ", flush=True)
    text = pdf_text(path, limit_pages=limit_pages)
    qs = dedup(parse_chapterwise(text))
    print(len(qs))
    return qs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aipgmee", action="store_true", help="AIPGMEE 2012–2016")
    ap.add_argument("--aipgmee-gap", action="store_true", help="AIPGMEE 2017–2018 (not yet in merge)")
    ap.add_argument("--nishant-2019-2020", action="store_true", help="Nishant NEETPG 2019–2020")
    ap.add_argument("--fmge-years", action="store_true")
    ap.add_argument("--fmge-2024-2025", action="store_true", help="fmgeplans standalone 2024/2025 PDFs")
    ap.add_argument("--chapterwise", action="store_true")
    ap.add_argument("--gaps", action="store_true", help="All known local extraction gaps")
    ap.add_argument("--limit-pages", type=int, default=0, help="Smoke-test first N pages")
    args = ap.parse_args()
    do_all = not any(
        [
            args.aipgmee,
            args.aipgmee_gap,
            args.nishant_2019_2020,
            args.fmge_years,
            args.fmge_2024_2025,
            args.chapterwise,
            args.gaps,
        ]
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if do_all or args.aipgmee:
        print("=== AIPGMEE 2012–2016 ===")
        qs = extract_aipgmee(args.limit_pages, years=range(2012, 2017))
        out = OUT_DIR / "q_aipgmee_2012_2016.json"
        out.write_text(json.dumps(qs, indent=2, ensure_ascii=False))
        print(f"Saved {len(qs)} → {out}")

    if do_all or args.gaps or args.aipgmee_gap:
        print("\n=== AIPGMEE 2017–2018 (gap) ===")
        qs = extract_aipgmee(args.limit_pages, years=(2017, 2018))
        out = OUT_DIR / "q_aipgmee_2017_2018.json"
        out.write_text(json.dumps(qs, indent=2, ensure_ascii=False))
        print(f"Saved {len(qs)} → {out}")

    if do_all or args.gaps or args.nishant_2019_2020:
        print("\n=== Nishant NEETPG 2019–2020 (gap) ===")
        qs = extract_nishant_neetpg_gap(args.limit_pages)
        out = OUT_DIR / "q_nishant_2019_2020.json"
        out.write_text(json.dumps(qs, indent=2, ensure_ascii=False))
        print(f"Saved {len(qs)} → {out}")

    if do_all or args.fmge_years:
        print("\n=== neetfmgeplans 2022/2023 (text extract — no vision needed) ===")
        qs = extract_fmge_years(args.limit_pages)
        out = OUT_DIR / "q_fmgeplans_2022_2023.json"
        out.write_text(json.dumps(qs, indent=2, ensure_ascii=False))
        print(f"Saved {len(qs)} → {out}")

    if do_all or args.gaps or args.fmge_2024_2025:
        print("\n=== neetfmgeplans 2024/2025 standalone (gap; may be thin) ===")
        qs = extract_fmge_years(args.limit_pages, years=(2024, 2025))
        out = OUT_DIR / "q_fmgeplans_2024_2025.json"
        out.write_text(json.dumps(qs, indent=2, ensure_ascii=False))
        print(f"Saved {len(qs)} → {out}")

    if do_all or args.chapterwise:
        print("\n=== neetfmgeplans chapterwise ===")
        qs = extract_chapterwise(args.limit_pages)
        out = OUT_DIR / "q_fmgeplans_chapterwise.json"
        out.write_text(json.dumps(qs, indent=2, ensure_ascii=False))
        print(f"Saved {len(qs)} → {out}")

    print("\nNext: python3 analysis/clean_merge.py && python3 analysis/classify_llm.py")


if __name__ == "__main__":
    main()
