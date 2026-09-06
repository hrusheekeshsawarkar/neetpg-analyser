#!/usr/bin/env python3
"""
Extract clinical images from Nishant Bhushan NEET PG / AIPGMEE PDFs.

Layouts covered:
  - PrepLadder style: "Ques No: N Subject: ..."
  - Compact 2024: "Ques N. ..."
  - Numbered AIPGMEE / older: "N. stem..."

Usage:
  python analysis/extract_images_nishant.py --years 2021-2024
  python analysis/extract_images_nishant.py --years 2018,2023 --patch-merged
  python analysis/extract_images_nishant.py --aipgmee --years 2016-2018
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

# Reuse pairing helpers from CollegeDunia extractor
import extract_images_collegedunia as cd  # noqa: E402

PDF_DIR = ROOT / "neet-pg-papers" / "nishant-bhushan"
DATA = ROOT / "analysis" / "data"
MERGED = DATA / "merged_questions.json"
OUT_IMG = DATA / "question_images" / "nishant"
MANIFEST = DATA / "image_extract_nishant.json"
REVIEW = ROOT / "analysis" / "reports" / "image_extract_nishant_review.html"

QUES_NO_RE = re.compile(r"(?i)ques(?:tion)?\s*no\.?\s*[:.]?\s*(\d{1,3})\b")
QUES_DOT_RE = re.compile(r"(?i)^\s*ques\s+(\d{1,3})\s*[.]\s*")
NUM_DOT_RE = re.compile(r"^\s*(\d{1,3})\.\s+(?=[A-Za-z(\[])")
# fmgeplans 2024: "Q.1. Which..." ; 2025: "... Q. The image..."
Q_DOT_NUM_RE = re.compile(r"(?i)\bQ\.?\s*(\d{1,3})\s*[.]\s+")
Q_BARE_RE = re.compile(r"(?i)\bQ\.\s+(?=[A-Za-z])")


def page_question_starts(page: fitz.Page) -> list[tuple[int, float, str]]:
    starts: list[tuple[int, float, str]] = []
    seen_y: list[float] = []
    bare_seq = 0
    for block in page.get_text("blocks"):
        raw = (block[4] or "").strip()
        if not raw:
            continue
        if float(block[0]) > 220:
            continue
        y0 = float(block[1])
        qnum = None
        m = QUES_NO_RE.search(raw)
        if m:
            qnum = int(m.group(1))
        if qnum is None:
            m = QUES_DOT_RE.match(raw)
            if m:
                qnum = int(m.group(1))
        if qnum is None:
            m = Q_DOT_NUM_RE.search(raw)
            if m:
                qnum = int(m.group(1))
        if qnum is None:
            m = NUM_DOT_RE.match(raw)
            if m:
                qnum = int(m.group(1))
        if qnum is None and Q_BARE_RE.search(raw):
            bare_seq += 1
            qnum = bare_seq + 900  # page-local synthetic ids (avoid clashing with real nums)
        if qnum is None or qnum < 1 or qnum > 999:
            continue
        if any(abs(y0 - sy) < 10 for sy in seen_y):
            continue
        snippet = re.sub(r"\s+", " ", raw)[:160]
        starts.append((qnum, y0, snippet))
        seen_y.append(y0)
    starts.sort(key=lambda t: t[1])
    return starts


IMAGE_CUE_RE = cd.IMAGE_CUE_RE


def parse_years(spec: str) -> list[int]:
    return cd.parse_years(spec)


def pdf_specs(years: list[int], include_aipgmee: bool, include_neetpg: bool) -> list[dict]:
    """Return list of {path, year, exam, source, shift}."""
    specs = []
    if include_neetpg:
        for year in years:
            if year < 2019:
                continue
            candidates = [
                (PDF_DIR / f"NEETPG-{year}.pdf", None),
                (PDF_DIR / f"NEETPG-{year}-shift1.pdf", "1"),
                (PDF_DIR / f"NEETPG-{year}-shift2.pdf", "2"),
            ]
            # Prefer canonical shift2 over *-direct duplicate
            direct = PDF_DIR / f"NEETPG-{year}-shift2-direct.pdf"
            shift2 = PDF_DIR / f"NEETPG-{year}-shift2.pdf"
            if direct.exists() and not shift2.exists():
                candidates.append((direct, "2"))
            seen = set()
            for path, shift in candidates:
                if not path.exists() or path.name in seen:
                    continue
                seen.add(path.name)
                specs.append(
                    {
                        "path": path,
                        "year": year,
                        "exam": "NEET PG",
                        "source": "nishant-neetpg",
                        "shift": shift,
                        "label": path.stem,
                    }
                )
    if include_aipgmee:
        for year in years:
            if year > 2018:
                continue
            path = PDF_DIR / f"AIPGMEE-{year}.pdf"
            if not path.exists():
                continue
            specs.append(
                {
                    "path": path,
                    "year": year,
                    "exam": "AIPGMEE",
                    "source": "nishant-aipgmee",
                    "shift": None,
                    "label": path.stem,
                }
            )
    return specs


def is_clinical_image(width: int, height: int, display: fitz.Rect) -> bool:
    if not cd.is_clinical_image(width, height, display):
        return False
    # Nishant / CollegeHai footer branding strip
    if width == 512 and height == 238 and display.y0 > 650:
        return False
    if display.y0 > 700 and display.height < 80 and width > 400:
        return False
    return True


def page_clinical_images(page: fitz.Page, doc: fitz.Document) -> list[dict]:
    out = []
    for info in page.get_image_info(xrefs=True):
        w, h = int(info.get("width") or 0), int(info.get("height") or 0)
        bbox = fitz.Rect(info["bbox"])
        if not is_clinical_image(w, h, bbox):
            continue
        out.append(
            {
                "xref": info.get("xref"),
                "width": w,
                "height": h,
                "bbox": [round(bbox.x0, 1), round(bbox.y0, 1), round(bbox.x1, 1), round(bbox.y1, 1)],
                "y0": float(bbox.y0),
                "y1": float(bbox.y1),
                "yc": float((bbox.y0 + bbox.y1) / 2),
            }
        )
    out.sort(key=lambda d: d["y0"])
    return out


def load_merged_index() -> dict[tuple[str, int, str], list[dict]]:
    """(source, year, question_number) -> rows."""
    if not MERGED.exists():
        return {}
    rows = json.loads(MERGED.read_text())
    idx: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for row in rows:
        src = row.get("source") or ""
        if src not in {"nishant-neetpg", "nishant-aipgmee"}:
            continue
        year = row.get("year")
        qn = str(row.get("question_number") or "").strip()
        if year is None or not qn:
            continue
        idx[(src, int(year), qn)].append(row)
    return idx


def process_pdf(spec: dict, merged_idx: dict) -> dict:
    path: Path = spec["path"]
    year = spec["year"]
    source = spec["source"]
    result = {
        "year": year,
        "source": source,
        "label": spec["label"],
        "pdf": str(path.relative_to(ROOT)),
        "shift": spec.get("shift"),
        "pages": 0,
        "clinical_images_found": 0,
        "questions_detected": 0,
        "image_cue_questions": 0,
        "linked": 0,
        "cue_unlinked": 0,
        "orphan_images": 0,
        "items": [],
        "errors": [],
    }

    out_dir = OUT_IMG / spec["label"]
    if out_dir.exists():
        for p in out_dir.glob("*"):
            if p.is_file():
                p.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Suppress noisy MuPDF broken-xref spam for some Nishant files
    doc = fitz.open(path)
    result["pages"] = len(doc)

    pages_data = []
    for page_i in range(len(doc)):
        page = doc[page_i]
        starts = page_question_starts(page)
        images = page_clinical_images(page, doc)
        result["clinical_images_found"] += len(images)
        result["questions_detected"] += len(starts)
        pages_data.append({"starts": starts, "images": images, "page": page})

    carry_item = None
    for page_i, pdata in enumerate(pages_data):
        page = pdata["page"]
        starts = pdata["starts"]
        images = pdata["images"]
        page_h = float(page.rect.height)
        assigned: set[int] = set()
        first_q_y = starts[0][1] if starts else page_h

        leading = [(ii, im) for ii, im in enumerate(images) if im["yc"] < first_q_y - 5]
        if carry_item and leading:
            saved = cd._save_images(doc, out_dir, carry_item["_qnum"], page_i, leading, result)
            if saved:
                carry_item["images"].extend(saved)
                for ii, _ in leading:
                    assigned.add(ii)
                carry_item["status"] = (
                    "linked" if carry_item.get("in_merged") else "linked_no_merge_row"
                )
                carry_item = None

        page_items = []
        for qi, (qnum, y0, snippet) in enumerate(starts):
            y1 = starts[qi + 1][1] if qi + 1 < len(starts) else page_h
            qtext = cd.question_text_in_range(page, y0, y1)
            cue = bool(IMAGE_CUE_RE.search(qtext) or IMAGE_CUE_RE.search(snippet))
            if cue:
                result["image_cue_questions"] += 1

            band = []
            for ii, im in enumerate(images):
                if ii in assigned:
                    continue
                if im["yc"] >= y0 - 5 and im["y0"] < y1 - 5:
                    band.append((ii, im))

            if not band and not cue:
                continue

            saved = cd._save_images(doc, out_dir, qnum, page_i, band, result) if band else []
            for ii, _ in band:
                assigned.add(ii)

            candidates = merged_idx.get((source, year, str(qnum)), [])
            # Prefer same shift when present
            row = None
            if candidates:
                if spec.get("shift"):
                    row = next(
                        (r for r in candidates if str(r.get("shift") or "") == str(spec["shift"])),
                        candidates[0],
                    )
                else:
                    row = candidates[0]

            qid = cd.make_qid(row) if row else None
            if not qid:
                stem = cd.normalize_stem(qtext or snippet)[:200]
                qid = hashlib.sha256(
                    f"{year}|{source}|{spec.get('shift') or ''}|{qnum}|{stem}".encode()
                ).hexdigest()

            item = {
                "year": year,
                "source": source,
                "label": spec["label"],
                "shift": spec.get("shift"),
                "page": page_i + 1,
                "question_number": str(qnum),
                "qid": qid,
                "status": "linked" if (saved and row) else (
                    "linked_no_merge_row" if saved else "cue_unlinked"
                ),
                "in_merged": bool(row),
                "has_image_cue": cue or cd.has_image_ref(qtext),
                "ask_type": (row or {}).get("ask_type"),
                "subject": (row or {}).get("subject_clean") or (row or {}).get("subject"),
                "question_preview": (qtext or snippet)[:220],
                "question_text": (row or {}).get("question_text") or (qtext or "")[:400],
                "images": saved,
                "_qnum": qnum,
            }
            page_items.append(item)

        for ii, im in enumerate(images):
            if ii in assigned:
                continue
            q_y = {qnum: y0 for qnum, y0, _ in starts}
            candidates = [it for it in page_items if q_y.get(it["_qnum"], 0) <= im["yc"]]
            if not candidates and carry_item:
                target = carry_item
            elif candidates:
                target = max(candidates, key=lambda it: q_y.get(it["_qnum"], 0))
            else:
                result["orphan_images"] += 1
                continue
            saved = cd._save_images(doc, out_dir, target["_qnum"], page_i, [(ii, im)], result)
            if saved:
                target["images"].extend(saved)
                assigned.add(ii)
                target["status"] = (
                    "linked" if target.get("in_merged") else "linked_no_merge_row"
                )
                if target is carry_item and target["images"]:
                    carry_item = None
            else:
                result["orphan_images"] += 1

        for it in page_items:
            result["items"].append(it)

        carry_item = None
        if page_items:
            last = page_items[-1]
            last_y = next((y0 for qn, y0, _ in starts if qn == last["_qnum"]), 0)
            if not last["images"] and last.get("has_image_cue") and last_y > page_h * 0.55:
                carry_item = last

    for it in result["items"]:
        it.pop("_qnum", None)
        if it.get("images"):
            it["status"] = "linked" if it.get("in_merged") else "linked_no_merge_row"
        elif it.get("has_image_cue"):
            it["status"] = "cue_unlinked"

    result["linked"] = sum(1 for it in result["items"] if it.get("images"))
    result["cue_unlinked"] = sum(
        1 for it in result["items"] if not it.get("images") and it.get("has_image_cue")
    )
    doc.close()
    return result


def patch_merged(items: list[dict]) -> int:
    rows = json.loads(MERGED.read_text())
    by_qid = {}
    by_key = {}
    for it in items:
        if not it.get("images"):
            continue
        paths = [im["path"] for im in it["images"]]
        payload = {
            "images": paths,
            "image_status": "linked",
            "image_source": it.get("source") or "nishant",
        }
        if it.get("qid"):
            by_qid[it["qid"]] = payload
        by_key[(it.get("source"), it["year"], str(it["question_number"]))] = payload

    n = 0
    for row in rows:
        src = row.get("source")
        if src not in {"nishant-neetpg", "nishant-aipgmee"}:
            continue
        # Don't overwrite collegedunia (or other) images already attached
        if row.get("images") and row.get("image_source") not in {None, "", src, "nishant"}:
            continue
        qid = cd.make_qid(row)
        payload = by_qid.get(qid) or by_key.get((src, row.get("year"), str(row.get("question_number") or "")))
        if not payload:
            continue
        row.update(payload)
        n += 1
    MERGED.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return n


def write_review(items: list[dict], summary: dict) -> None:
    # Monkey-patch REVIEW path used by cd.write_review_html by writing our own
    cd.REVIEW = REVIEW
    # Adapt title via temporary rewrite
    cd.write_review_html(items, summary)
    text = REVIEW.read_text(encoding="utf-8")
    text = text.replace(
        "CollegeDunia image extraction — review",
        "Nishant image extraction — review",
    ).replace(
        "CollegeDunia image extract review",
        "Nishant image extract review",
    )
    REVIEW.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", default="2021-2024", help="e.g. 2023 or 2016-2018 or 2021,2024")
    ap.add_argument("--neetpg", action="store_true", help="Only NEETPG PDFs")
    ap.add_argument("--aipgmee", action="store_true", help="Only AIPGMEE PDFs")
    ap.add_argument("--patch-merged", action="store_true")
    args = ap.parse_args()

    years = parse_years(args.years)
    include_neetpg = args.neetpg or not args.aipgmee
    include_aipgmee = args.aipgmee or not args.neetpg
    if args.neetpg and not args.aipgmee:
        include_aipgmee = False
    if args.aipgmee and not args.neetpg:
        include_neetpg = False

    specs = pdf_specs(years, include_aipgmee=include_aipgmee, include_neetpg=include_neetpg)
    if not specs:
        raise SystemExit(f"No Nishant PDFs found for years={years}")

    merged_idx = load_merged_index()
    print(f"Nishant image extract — {len(specs)} PDFs, years={years}")
    print(f"Merged nishant index keys: {len(merged_idx)}")

    pdf_results = []
    all_items: list[dict] = []
    for spec in specs:
        print(f"\n=== {spec['label']} ===")
        r = process_pdf(spec, merged_idx)
        pdf_results.append(r)
        all_items.extend(r["items"])
        print(
            f"  pages={r['pages']} clinical={r['clinical_images_found']} "
            f"qs={r['questions_detected']} cues={r['image_cue_questions']} "
            f"linked={r['linked']} cue_unlinked={r['cue_unlinked']} orphans={r['orphan_images']}"
        )

    summary = {
        "years": years,
        "pdfs": [s["label"] for s in specs],
        "linked": sum(r["linked"] for r in pdf_results),
        "cue_unlinked": sum(r["cue_unlinked"] for r in pdf_results),
        "clinical_images_found": sum(r["clinical_images_found"] for r in pdf_results),
        "orphan_images": sum(r["orphan_images"] for r in pdf_results),
        "image_cue_questions": sum(r["image_cue_questions"] for r in pdf_results),
        "in_merged": sum(1 for it in all_items if it.get("in_merged") and it.get("images")),
        "out_dir": str(OUT_IMG.relative_to(ROOT)),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "review": str(REVIEW.relative_to(ROOT)),
    }
    MANIFEST.write_text(
        json.dumps({"summary": summary, "pdfs": pdf_results, "items": all_items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_review(all_items, summary)

    if args.patch_merged:
        n = patch_merged([it for it in all_items if it.get("images")])
        print(f"\nPatched merged_questions.json rows: {n}")

    print("\n=== DONE ===")
    print(json.dumps(summary, indent=2))
    print(f"Review: {REVIEW}")


if __name__ == "__main__":
    main()
