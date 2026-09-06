#!/usr/bin/env python3
"""
Extract NEET PG memory banks from FirstRanker PDFs (answers + explanations).

Formats covered:
  2012–2016, 2018–2020  numbered  "1. ... a) ... Correct Answer - A" + explanation
  2017                  "Question N" / A> ... / Answer - X / Explanation -
  2022–2023             "Ques No: N" / Subject / Topic / O1..O4 / Ans
  2024 shift1/shift2    "Ques N. ..." / a. ... / Ans. x
  2021                  scanned images → OpenRouter free OCR (page batches)

Usage:
  python analysis/extract_firstranker.py                 # all text years
  python analysis/extract_firstranker.py --ocr-2021      # scanned 2021
  python analysis/extract_firstranker.py --years 2022,2023,2024
  python analysis/extract_firstranker.py --limit-pages 20 # smoke

Then:
  python analysis/clean_merge.py
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import fitz  # pymupdf

from llm_client import call_llm_vision, extract_json

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "neet-pg-papers" / "firstranker"
OUT_DIR = ROOT / "analysis" / "data"
OCR_DIR = PDF_DIR / "_ocr"
ANS_MAP = {"A": "1", "B": "2", "C": "3", "D": "4", "a": "1", "b": "2", "c": "3", "d": "4"}

WATERMARK_RE = re.compile(
    r"(?i)(?:www\.)?firstranker\.com|---\s*Content provided by.*?---",
)


def clean_noise(text: str) -> str:
    # Replace watermarks with a space (do NOT eat surrounding newlines —
    # that would glue "stem:" onto "a)" and break MCQ parsing).
    text = WATERMARK_RE.sub(" ", text or "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def pdf_text(path: Path, limit_pages: int = 0) -> str:
    doc = fitz.open(path)
    parts = []
    n = min(limit_pages, doc.page_count) if limit_pages else doc.page_count
    for i in range(n):
        parts.append(doc[i].get_text() or "")
    return clean_noise("\n".join(parts))


def _opts_abcd(body: str) -> tuple[list[str], str]:
    """Return ([o1..o4], stem) from a/b/c/d or A> style options."""
    opts = re.findall(r"(?m)^\s*([a-dA-D])[\)\.>]\s*(.+)$", body)
    if len(opts) < 2:
        opts = re.findall(r"\b([a-dA-D])\)\s*([^a-dA-D\n]{2,200})", body)
    clean = ["", "", "", ""]
    for lab, val in opts[:4]:
        idx = ord(lab.upper()) - ord("A")
        if 0 <= idx < 4:
            v = WATERMARK_RE.sub(" ", val)
            clean[idx] = re.sub(r"\s+", " ", v).strip()[:300]
    m = re.search(r"(?m)^\s*[a-dA-D][\)\.>]\s*", body)
    if not m:
        m = re.search(r"\b[a-dA-D]\)\s*", body)
    stem = body[: m.start()] if m else body
    stem = re.sub(r"\s+", " ", WATERMARK_RE.sub(" ", stem)).strip()
    return clean, stem


def _answer_and_note(block: str) -> tuple[str, str, str]:
    """Split body / answer(1-4) / explanation from a question block."""
    stop = re.search(
        r"(?is)(?:Correct Answer\s*[-:]\s*([A-Da-d])|"
        r"Answer\s*[-:]\s*([A-Da-d1-4])\.?|"
        r"Ans\.?\s*(?:is\s*)?['\"]?([A-Da-d1-4]))",
        block,
    )
    if not stop:
        return block, "", ""
    letter = (stop.group(1) or stop.group(2) or stop.group(3) or "").strip()
    answer = ANS_MAP.get(letter, letter if letter in "1234" else "")
    body = block[: stop.start()]
    tail = block[stop.end() :]
    # Drop "is 'a' i.e., ..." short lead-in; keep rest as explanation
    note = re.sub(
        r"(?is)^\s*(?:\.|is\s+['\"]?[a-d]['\"]?\s*(?:i\.e\.,?)?[^.\n]*)",
        "",
        tail,
        count=1,
    )
    note = re.sub(r"(?im)^\s*(Explanation\s*[-:]?\s*)", "", note)
    note = clean_noise(note)
    note = re.sub(r"\s+", " ", note).strip()[:2000]
    return body, answer, note


def parse_numbered(text: str, year: int, source: str) -> list[dict]:
    """'1. stem ... a) ... Correct Answer - A' + explanation."""
    # Anchor on real MCQs (number + a) ... Correct Answer) so explanation
    # sub-lists like "1. Secondary spermatocyte" do not split the paper.
    pat = re.compile(
        r"(?ms)(?:^|\n)\s*(\d{1,3})\.\s*\n?\s*(.*?)\n\s*[aA]\)\s*(.*?)"
        r"Correct Answer\s*-\s*([A-Da-d])\s*(.*?)(?=(?:\n\s*\d{1,3}\.\s*)|\Z)"
    )
    qs = []
    for m in pat.finditer(text):
        num, stem_raw, opt_blob, letter, tail = m.groups()
        answer = ANS_MAP.get(letter.strip(), "")
        stem = re.sub(r"\s+", " ", WATERMARK_RE.sub(" ", stem_raw)).strip()
        if len(stem) < 15 or len(stem) > 600:
            continue
        # Drop explanation/list fragments mistaken for stems
        if re.match(r"(?i)^(\d+[\).\s]|[-*•]|ref\.|page\s)", stem):
            continue
        if stem.count("?") == 0 and not re.search(
            r"(?i)\b(which|what|where|when|how|all of the following|true|false|except|most|least|cause|feature|treatment|diagnosis)\b",
            stem,
        ):
            # still keep if options look solid
            pass
        # Rebuild body for option parse
        body = stem_raw + "\na) " + opt_blob
        opts, _ = _opts_abcd(body)
        if sum(1 for o in opts if o) < 2:
            # fallback: parse a)/b)/c)/d) from opt_blob
            opts = ["", "", "", ""]
            full = "a) " + opt_blob
            found = re.findall(
                r"(?is)\b([a-dA-D])\)\s*(.*?)(?=\b[a-dA-D]\)|Correct Answer|\Z)",
                full,
            )
            for lab, val in found[:4]:
                idx = ord(lab.upper()) - ord("A")
                if 0 <= idx < 4:
                    opts[idx] = re.sub(
                        r"\s+", " ", WATERMARK_RE.sub(" ", val)
                    ).strip()[:300]
        if sum(1 for o in opts if o) < 2:
            continue
        # Heuristic: real MCQ stems aren't just comma-lists of drugs/terms
        if stem.count(",") >= 4 and "?" not in stem and len(stem) < 80:
            continue
        note = re.sub(
            r"(?is)^\s*(?:Answer\s*[-:]?\s*[A-Da-d]\.?[^\n]*\n?)?",
            "",
            tail,
            count=1,
        )
        note = re.sub(r"\s+", " ", clean_noise(note)).strip()[:2000]
        if len(note) < 20:
            note = ""
        qs.append(
            {
                "question_number": str(num),
                "year": year,
                "exam": "NEET PG" if year >= 2013 else "AIPGMEE",
                "source": source,
                "subject": "",
                "topic": "",
                "subtopic": "",
                "question_text": stem[:800],
                "option_1": opts[0],
                "option_2": opts[1],
                "option_3": opts[2],
                "option_4": opts[3],
                "answer": answer,
                "answer_note": note or None,
            }
        )
    return qs


def parse_question_n(text: str, year: int, source: str) -> list[dict]:
    """'Question 1' / A> ... / Answer - B / Explanation - ..."""
    parts = re.split(r"(?im)^\s*Question\s+(\d+)\s*$", text)
    qs = []
    for i in range(1, len(parts), 2):
        num = parts[i]
        block = parts[i + 1] if i + 1 < len(parts) else ""
        if len(block) < 20:
            continue
        body, answer, note = _answer_and_note(block)
        # Also capture explicit Explanation section if body still has answer text
        em = re.search(r"(?is)Explanation\s*[-:]?\s*(.+)$", block)
        if em and (not note or len(em.group(1)) > len(note)):
            note = clean_noise(em.group(1))
            note = re.sub(r"\s+", " ", note).strip()[:2000]
        opts, stem = _opts_abcd(body)
        if len(stem) < 12:
            continue
        qs.append(
            {
                "question_number": str(num),
                "year": year,
                "exam": "NEET PG" if year >= 2013 else "AIPGMEE",
                "source": source,
                "subject": "",
                "topic": "",
                "subtopic": "",
                "question_text": stem[:800],
                "option_1": opts[0],
                "option_2": opts[1],
                "option_3": opts[2],
                "option_4": opts[3],
                "answer": answer,
                "answer_note": note or None,
            }
        )
    return qs


def parse_ques_no(text: str, year: int, source: str) -> list[dict]:
    """PrepLadder-style Ques No / Subject / Topic / O1..O4 / Ans."""
    blocks = re.split(r"(?i)Ques\s*No\s*:\s*(\d+)", text)
    qs = []
    for i in range(1, len(blocks), 2):
        num = blocks[i]
        content = blocks[i + 1] if i + 1 < len(blocks) else ""
        subj_m = re.search(r"(?i)Subject\s*:\s*([^\n]+)", content)
        topic_m = re.search(r"(?i)Topic\s*:\s*([^\n]+)", content)
        q_m = re.search(
            r"(?is)Sub-Topic\s*:\s*[^\n]*\n(.*?)(?=\n\s*O\s*1\s*:)",
            content,
        )
        if not q_m:
            q_m = re.search(
                r"(?is)Topic\s*:\s*[^\n]*\n(?:\s*Sub-Topic\s*:\s*[^\n]*\n)?(.*?)(?=\n\s*O\s*1\s*:)",
                content,
            )
        q_text = (q_m.group(1) if q_m else "").strip()
        q_text = re.sub(r"(?im)^\s*(Subject|Topic|Sub-Topic)\s*:.*$", "", q_text).strip()
        q_text = re.sub(r"\s+", " ", WATERMARK_RE.sub(" ", q_text)).strip()
        if len(q_text) < 10:
            continue
        opts = {}
        for n in (1, 2, 3, 4):
            nxt = n + 1
            end = rf"\n\s*O\s*{nxt}\s*:" if n < 4 else r"\n\s*Ans\s*:"
            om = re.search(
                rf"(?is)\n\s*O\s*{n}\s*:\s*(.*?)(?={end}|\Z)",
                content,
            )
            if om:
                val = WATERMARK_RE.sub(" ", om.group(1))
                val = re.sub(r"\s+", " ", val).strip()
                # drop accidental next-option labels
                val = re.sub(r"(?i)\s*O\s*\d\s*:.*$", "", val).strip()
                if val:
                    opts[n] = val[:300]
        ans_m = re.search(r"(?i)Ans\s*:\s*(\d+|[A-D])", content)
        answer = ""
        if ans_m:
            a = ans_m.group(1)
            answer = ANS_MAP.get(a, a)
        note = ""
        nm = re.search(r"(?is)Ans\s*:\s*\S+\s*(.+)$", content)
        if nm:
            note = re.sub(r"\s+", " ", clean_noise(nm.group(1))).strip()[:2000]
            if len(note) < 20:
                note = ""
        qs.append(
            {
                "question_number": str(num),
                "year": year,
                "exam": "NEET PG",
                "source": source,
                "subject": (subj_m.group(1).strip() if subj_m else ""),
                "topic": (topic_m.group(1).strip() if topic_m else ""),
                "subtopic": "",
                "question_text": q_text[:800],
                "option_1": opts.get(1, ""),
                "option_2": opts.get(2, ""),
                "option_3": opts.get(3, ""),
                "option_4": opts.get(4, ""),
                "answer": answer,
                "answer_note": note or None,
            }
        )
    return qs


def parse_ques_dot(text: str, year: int, source: str, shift: int | None = None) -> list[dict]:
    """2024-style 'Ques 1. stem' / a. opt / Ans. c"""
    parts = re.split(r"(?im)^\s*Ques\.?\s*(\d+)\s*[\.\:\)]?\s*", text)
    qs = []
    for i in range(1, len(parts), 2):
        num = parts[i]
        block = parts[i + 1] if i + 1 < len(parts) else ""
        if len(block) < 15:
            continue
        am = re.search(r"(?im)^\s*Ans\.?\s*[:\.]?\s*([A-Da-d1-4])\b", block)
        answer = ""
        note = ""
        body = block
        if am:
            answer = ANS_MAP.get(am.group(1), am.group(1) if am.group(1) in "1234" else "")
            body = block[: am.start()]
            note = re.sub(r"\s+", " ", clean_noise(block[am.end() :])).strip()[:2000]
            if len(note) < 20:
                note = ""
        opts, stem = _opts_abcd(body)
        if len(stem) < 10:
            continue
        row = {
            "question_number": str(num),
            "year": year,
            "exam": "NEET PG",
            "source": source,
            "subject": "",
            "topic": "",
            "subtopic": "",
            "question_text": stem[:800],
            "option_1": opts[0],
            "option_2": opts[1],
            "option_3": opts[2],
            "option_4": opts[3],
            "answer": answer,
            "answer_note": note or None,
        }
        if shift:
            row["shift"] = shift
        qs.append(row)
    return qs


def dedup(qs: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for q in qs:
        text = (q.get("question_text") or "").strip()
        if len(text) < 10:
            continue
        key = (q.get("year"), text[:120].lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out


# year -> (filename glob fragment, parser kind, shift?)
CATALOG = [
    (2012, "FR_neet-pg-2012-question-paper-with-answers.pdf", "numbered", None),
    (2013, "FR_neet-pg-2013-question-paper-with-answers.pdf", "numbered", None),
    (2014, "FR_neet-pg-2014-question-paper-with-answers.pdf", "numbered", None),
    (2015, "FR_neet-pg-2015-question-paper-with-answers.pdf", "numbered", None),
    (2016, "FR_neet-pg-2016-question-paper-with-answers.pdf", "numbered", None),
    (2017, "FR_neet-pg-2017-question-paper-with-answers.pdf", "question_n", None),
    (2018, "FR_neet-pg-2018-question-paper-with-answers.pdf", "numbered", None),
    (2019, "FR_neet-pg-2019-question-paper-with-answers.pdf", "numbered", None),
    (2020, "FR_neet-pg-2020-question-paper-with-answers.pdf", "numbered", None),
    (2021, "FR_neet-pg-2021-previous-year-question-paper.pdf", "ocr", None),
    (2022, "FR_neet-pg-2022-question-paper-with-solutions.pdf", "ques_no", None),
    (2023, "FR_neet-pg-2023-question-paper-with-solutions.pdf", "ques_no", None),
    (2024, "FR_neet-pg-2024-shift-1-question-paper.pdf", "ques_dot", 1),
    (2024, "FR_neet-pg-2024-shift-2-question-paper.pdf", "ques_dot", 2),
]


def extract_year(
    year: int,
    filename: str,
    kind: str,
    shift: int | None,
    limit_pages: int = 0,
) -> list[dict]:
    path = PDF_DIR / filename
    if not path.exists():
        print(f"  missing {path.name}")
        return []
    source = f"firstranker-{year}" + (f"-s{shift}" if shift else "")
    print(f"  {path.name} [{kind}]...", end=" ", flush=True)
    if kind == "ocr":
        print("skip (use --ocr-2021)")
        return []
    text = pdf_text(path, limit_pages=limit_pages)
    if kind == "numbered":
        qs = parse_numbered(text, year, source)
    elif kind == "question_n":
        qs = parse_question_n(text, year, source)
    elif kind == "ques_no":
        qs = parse_ques_no(text, year, source)
    elif kind == "ques_dot":
        qs = parse_ques_dot(text, year, source, shift=shift)
    else:
        qs = []
    print(f"{len(qs)} qs  ans={sum(1 for q in qs if q.get('answer'))}  notes={sum(1 for q in qs if q.get('answer_note'))}")
    return qs


OCR_PROMPT = """Extract every NEET PG / medical MCQ visible on this page image.
Return ONLY a JSON array. Each object:
{
  "question_number": "1",
  "question_text": "...",
  "option_1": "...",
  "option_2": "...",
  "option_3": "...",
  "option_4": "...",
  "answer": "1"|"2"|"3"|"4"|"" ,
  "answer_note": "short explanation if present else null",
  "subject": "" ,
  "topic": ""
}
Rules:
- answer is the correct option number 1-4 when shown (A=1 B=2 C=3 D=4).
- Skip watermarks like FirstRanker.com.
- If a question spans pages and is incomplete, still extract what you see.
- No markdown fences, no commentary.
"""


def ocr_2021(limit_pages: int = 0, start_page: int = 0, batch_sleep: float = 1.5) -> list[dict]:
    """Render scanned 2021 pages and OCR via OpenRouter free vision models."""
    path = PDF_DIR / "FR_neet-pg-2021-previous-year-question-paper.pdf"
    if not path.exists():
        print("  missing 2021 PDF")
        return []
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    ckpt = OCR_DIR / "ocr_2021_checkpoint.json"
    done: dict[str, list] = {}
    if ckpt.exists():
        done = json.loads(ckpt.read_text())
        print(f"  resume OCR checkpoint: {len(done)} pages")

    doc = fitz.open(path)
    n = doc.page_count
    end = min(n, start_page + limit_pages) if limit_pages else n
    all_qs: list[dict] = []
    # reload prior pages' questions
    for k in sorted(done, key=lambda x: int(x)):
        all_qs.extend(done[k])

    for i in range(start_page, end):
        key = str(i)
        if key in done:
            continue
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        img = pix.tobytes("png")
        print(f"  OCR page {i+1}/{n}...", end=" ", flush=True)
        try:
            raw = call_llm_vision(OCR_PROMPT, img, mime="image/png", max_tokens=4000)
            parsed = extract_json(raw)
            if not isinstance(parsed, list):
                parsed = []
            rows = []
            for q in parsed:
                if not isinstance(q, dict):
                    continue
                text = (q.get("question_text") or "").strip()
                if len(text) < 10:
                    continue
                ans = str(q.get("answer") or "").strip()
                if ans.upper() in ANS_MAP:
                    ans = ANS_MAP[ans.upper()]
                rows.append(
                    {
                        "question_number": str(q.get("question_number") or ""),
                        "year": 2021,
                        "exam": "NEET PG",
                        "source": "firstranker-2021-ocr",
                        "subject": q.get("subject") or "",
                        "topic": q.get("topic") or "",
                        "subtopic": "",
                        "question_text": text[:800],
                        "option_1": (q.get("option_1") or "")[:300],
                        "option_2": (q.get("option_2") or "")[:300],
                        "option_3": (q.get("option_3") or "")[:300],
                        "option_4": (q.get("option_4") or "")[:300],
                        "answer": ans if ans in "1234" else "",
                        "answer_note": q.get("answer_note") or None,
                        "ocr_page": i + 1,
                    }
                )
            done[key] = rows
            all_qs.extend(rows)
            ckpt.write_text(json.dumps(done, ensure_ascii=False))
            print(f"{len(rows)} qs")
        except Exception as e:
            # Do not checkpoint failures — leave page unset so --ocr-2021 can resume.
            print(f"FAIL {e}")
        time.sleep(batch_sleep)
    return dedup(all_qs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=str, default="", help="comma years e.g. 2022,2023,2024")
    ap.add_argument("--limit-pages", type=int, default=0)
    ap.add_argument("--ocr-2021", action="store_true")
    ap.add_argument("--ocr-start", type=int, default=0)
    ap.add_argument("--ocr-sleep", type=float, default=1.5)
    args = ap.parse_args()

    want = None
    if args.years:
        want = {int(x.strip()) for x in args.years.split(",") if x.strip()}

    all_qs: list[dict] = []
    # Text years: only page-limit when NOT doing a dedicated OCR run
    text_limit = 0 if args.ocr_2021 else args.limit_pages
    for year, fname, kind, shift in CATALOG:
        if want is not None and year not in want:
            continue
        if kind == "ocr":
            continue
        if args.ocr_2021 and want is None:
            # OCR-only mode unless years explicitly requested with OCR
            continue
        all_qs.extend(extract_year(year, fname, kind, shift, limit_pages=text_limit))

    if args.ocr_2021 and (want is None or 2021 in want):
        print("OCR 2021 scanned PDF via OpenRouter vision...")
        ocr_qs = ocr_2021(
            limit_pages=args.limit_pages,
            start_page=args.ocr_start,
            batch_sleep=args.ocr_sleep,
        )
        # Merge OCR into existing extract file rather than wiping it
        existing_path = OUT_DIR / "q_firstranker.json"
        existing: list[dict] = []
        if existing_path.exists() and not args.years:
            try:
                existing = json.loads(existing_path.read_text())
                existing = [q for q in existing if q.get("source") != "firstranker-2021-ocr"]
            except Exception:
                existing = []
        all_qs = dedup(existing + all_qs + ocr_qs)
        existing_path.write_text(json.dumps(all_qs, indent=2, ensure_ascii=False))
        ans_n = sum(1 for q in all_qs if q.get("answer"))
        note_n = sum(1 for q in all_qs if q.get("answer_note"))
        print(f"\nSaved {len(all_qs)} questions → {existing_path}")
        print(f"  with answer: {ans_n}  with explanation: {note_n}")
        return

    all_qs = dedup(all_qs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "q_firstranker.json"
    out.write_text(json.dumps(all_qs, indent=2, ensure_ascii=False))
    ans_n = sum(1 for q in all_qs if q.get("answer"))
    note_n = sum(1 for q in all_qs if q.get("answer_note"))
    print(f"\nSaved {len(all_qs)} questions → {out}")
    print(f"  with answer: {ans_n}  with explanation: {note_n}")


if __name__ == "__main__":
    main()
