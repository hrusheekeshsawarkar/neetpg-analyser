#!/usr/bin/env python3
"""
Extract clinical images from FirstRanker NEET PG PDFs.

Layouts:
  2022–2023   PrepLadder "Ques No: N"
  2024 s1/s2  "Ques N. ..."
  2012–2020   numbered "N. stem" / a) b) c) d)  (sparse figures)
  2021        full-page scans — skipped (no selectable stems)

Usage:
  python analysis/extract_images_firstranker.py --years 2022-2024
  python analysis/extract_images_firstranker.py --years 2018,2022,2023,2024
  python analysis/extract_images_firstranker.py --years 2022-2024 --patch-merged
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

import extract_images_collegedunia as cd  # noqa: E402
import extract_images_nishant as ns  # noqa: E402

PDF_DIR = ROOT / "neet-pg-papers" / "firstranker"
DATA = ROOT / "analysis" / "data"
MERGED = DATA / "merged_questions.json"
OUT_IMG = DATA / "question_images" / "firstranker"
MANIFEST = DATA / "image_extract_firstranker.json"
REVIEW = ROOT / "analysis" / "reports" / "image_extract_firstranker_review.html"

# Mirror extract_firstranker.py inventory
PDF_SPECS = [
    (2012, "FR_neet-pg-2012-question-paper-with-answers.pdf", "firstranker-2012", None),
    (2013, "FR_neet-pg-2013-question-paper-with-answers.pdf", "firstranker-2013", None),
    (2014, "FR_neet-pg-2014-question-paper-with-answers.pdf", "firstranker-2014", None),
    (2015, "FR_neet-pg-2015-question-paper-with-answers.pdf", "firstranker-2015", None),
    (2016, "FR_neet-pg-2016-question-paper-with-answers.pdf", "firstranker-2016", None),
    (2017, "FR_neet-pg-2017-question-paper-with-answers.pdf", "firstranker-2017", None),
    (2018, "FR_neet-pg-2018-question-paper-with-answers.pdf", "firstranker-2018", None),
    (2019, "FR_neet-pg-2019-question-paper-with-answers.pdf", "firstranker-2019", None),
    (2020, "FR_neet-pg-2020-question-paper-with-answers.pdf", "firstranker-2020", None),
    # 2021 scanned — skip
    (2022, "FR_neet-pg-2022-question-paper-with-solutions.pdf", "firstranker-2022", None),
    (2023, "FR_neet-pg-2023-question-paper-with-solutions.pdf", "firstranker-2023", None),
    (2024, "FR_neet-pg-2024-shift-1-question-paper.pdf", "firstranker-2024-s1", "1"),
    (2024, "FR_neet-pg-2024-shift-2-question-paper.pdf", "firstranker-2024-s2", "2"),
]

NUM_DOT_RE = re.compile(r"^\s*(\d{1,3})\.\s+(?=[A-Za-z(\[])")
QUESTION_N_RE = re.compile(r"(?i)^\s*Question\s+(\d{1,3})\b")


def parse_years(spec: str) -> list[int]:
    return cd.parse_years(spec)


def is_clinical_image(width: int, height: int, display: fitz.Rect) -> bool:
    if not cd.is_clinical_image(width, height, display):
        return False
    # FirstRanker header/footer watermark strips (often 240×34)
    if width <= 260 and height <= 50:
        return False
    if display.height < 35 and display.width > 150:
        return False
    # tiny corner stamps
    if display.y0 < 40 and display.height < 50:
        return False
    if display.y0 > 780 and display.height < 50:
        return False
    return True


def page_clinical_images(page: fitz.Page) -> list[dict]:
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


def page_question_starts(page: fitz.Page) -> list[tuple[int, float, str]]:
    """PrepLadder / Ques N / numbered / Question N."""
    starts = ns.page_question_starts(page)
    if len(starts) >= 2:
        return starts
    # Fallback numbered / Question N for older FR
    seen_y: list[float] = []
    extra: list[tuple[int, float, str]] = []
    for block in page.get_text("blocks"):
        raw = (block[4] or "").strip()
        if not raw or float(block[0]) > 220:
            continue
        y0 = float(block[1])
        qnum = None
        m = QUESTION_N_RE.match(raw)
        if m:
            qnum = int(m.group(1))
        if qnum is None:
            m = NUM_DOT_RE.match(raw)
            if m:
                qnum = int(m.group(1))
        if qnum is None or qnum < 1 or qnum > 400:
            continue
        if any(abs(y0 - sy) < 10 for sy in seen_y):
            continue
        extra.append((qnum, y0, re.sub(r"\s+", " ", raw)[:160]))
        seen_y.append(y0)
    if len(extra) > len(starts):
        return sorted(extra, key=lambda t: t[1])
    return starts


def load_merged_index() -> dict[tuple[str, int, str], list[dict]]:
    if not MERGED.exists():
        return {}
    rows = json.loads(MERGED.read_text())
    idx: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for row in rows:
        src = row.get("source") or ""
        if not src.startswith("firstranker"):
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

    doc = fitz.open(path)
    result["pages"] = len(doc)

    # Skip fully scanned docs (almost no text)
    sample_text = "".join((doc[i].get_text() or "") for i in range(min(3, len(doc))))
    if len(sample_text.strip()) < 80:
        result["errors"].append("scanned_or_empty_text — skipped")
        doc.close()
        return result

    pages_data = []
    for page_i in range(len(doc)):
        page = doc[page_i]
        starts = page_question_starts(page)
        images = page_clinical_images(page)
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
            # Drop watermark noise from text
            qtext = re.sub(r"(?i)www\.firstranker\.com", " ", qtext)
            qtext = re.sub(r"\s+", " ", qtext).strip()
            cue = bool(cd.IMAGE_CUE_RE.search(qtext) or cd.IMAGE_CUE_RE.search(snippet))
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

            cands = merged_idx.get((source, year, str(qnum)), [])
            row = cands[0] if cands else None
            qid = cd.make_qid(row) if row else None
            if not qid:
                stem = cd.normalize_stem(qtext or snippet)[:200]
                qid = hashlib.sha256(
                    f"{year}|{source}|{spec.get('shift') or ''}|{qnum}|{stem}".encode()
                ).hexdigest()

            # Prefer stem before Ans
            display = re.split(r"\bAns\s*[.:]", qtext or snippet, maxsplit=1, flags=re.I)[0]
            display = re.sub(r"\s+", " ", display).strip()[:400]

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
                "has_image_cue": cue or cd.has_image_ref(display),
                "ask_type": (row or {}).get("ask_type"),
                "subject": (row or {}).get("subject_clean") or (row or {}).get("subject"),
                "question_preview": display[:220],
                "question_text": (row or {}).get("question_text") or display,
                "images": saved,
                "_qnum": qnum,
                "_cue": cue,
            }
            page_items.append(item)

        # Orphans → only cue stems still missing a figure
        for ii, im in enumerate(images):
            if ii in assigned:
                continue
            q_y = {qnum: y0 for qnum, y0, _ in starts}
            cands = [
                it
                for it in page_items
                if it.get("_cue")
                and not it["images"]
                and q_y.get(it["_qnum"], 0) <= im["yc"]
            ]
            if not cands:
                result["orphan_images"] += 1
                continue
            target = max(cands, key=lambda it: q_y.get(it["_qnum"], 0))
            if im["y0"] - q_y.get(target["_qnum"], 0) > 320:
                result["orphan_images"] += 1
                continue
            saved = cd._save_images(doc, out_dir, target["_qnum"], page_i, [(ii, im)], result)
            if saved:
                target["images"].extend(saved)
                assigned.add(ii)
                target["status"] = (
                    "linked" if target.get("in_merged") else "linked_no_merge_row"
                )
            else:
                result["orphan_images"] += 1

        for it in page_items:
            result["items"].append(it)

        carry_item = None
        if page_items:
            last = page_items[-1]
            last_y = next((y0 for qn, y0, _ in starts if qn == last["_qnum"]), 0)
            if not last["images"] and last.get("_cue") and last_y > page_h * 0.55:
                carry_item = last

    for it in result["items"]:
        it.pop("_qnum", None)
        it.pop("_cue", None)
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
        # Don't overwrite better prior sources when patching by key alone
        payload = {
            "images": [im["path"] for im in it["images"]],
            "image_status": "linked",
            "image_source": it.get("source") or "firstranker",
        }
        if it.get("qid"):
            by_qid[it["qid"]] = payload
        by_key[(it.get("source"), it["year"], str(it["question_number"]))] = payload

    n = 0
    for row in rows:
        src = row.get("source") or ""
        if not src.startswith("firstranker"):
            continue
        if row.get("images") and row.get("image_source") not in {
            None,
            "",
            src,
            "firstranker",
        }:
            continue
        qid = cd.make_qid(row)
        payload = by_qid.get(qid) or by_key.get(
            (src, row.get("year"), str(row.get("question_number") or ""))
        )
        if not payload:
            continue
        row.update(payload)
        n += 1
    MERGED.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return n


def write_review(items: list[dict], summary: dict) -> None:
    cd.REVIEW = REVIEW
    cd.write_review_html(items, summary)
    text = REVIEW.read_text(encoding="utf-8")
    text = text.replace(
        "CollegeDunia image extraction — review",
        "FirstRanker image extraction — review",
    ).replace("CollegeDunia image extract review", "FirstRanker image extract review")
    REVIEW.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", default="2022-2024", help="e.g. 2022-2024 or 2018,2023")
    ap.add_argument("--patch-merged", action="store_true")
    args = ap.parse_args()

    years = set(parse_years(args.years))
    specs = []
    for year, fname, source, shift in PDF_SPECS:
        if year not in years:
            continue
        path = PDF_DIR / fname
        if not path.exists():
            print(f"  skip missing {fname}")
            continue
        specs.append(
            {
                "path": path,
                "year": year,
                "source": source,
                "shift": shift,
                "label": path.stem,
            }
        )
    if not specs:
        raise SystemExit(f"No FirstRanker PDFs for years={sorted(years)}")

    merged_idx = load_merged_index()
    print(f"FirstRanker image extract — {len(specs)} PDFs, years={sorted(years)}")
    print(f"Merged firstranker index keys: {len(merged_idx)}")

    results = []
    all_items: list[dict] = []
    for spec in specs:
        print(f"\n=== {spec['label']} ===")
        r = process_pdf(spec, merged_idx)
        results.append(r)
        all_items.extend(r["items"])
        err = f" errors={r['errors']}" if r["errors"] else ""
        print(
            f"  pages={r['pages']} clinical={r['clinical_images_found']} "
            f"qs={r['questions_detected']} cues={r['image_cue_questions']} "
            f"linked={r['linked']} cue_unlinked={r['cue_unlinked']} "
            f"orphans={r['orphan_images']}{err}"
        )

    summary = {
        "years": sorted(years),
        "pdfs": [r["label"] for r in results],
        "linked": sum(r["linked"] for r in results),
        "cue_unlinked": sum(r["cue_unlinked"] for r in results),
        "clinical_images_found": sum(r["clinical_images_found"] for r in results),
        "orphan_images": sum(r["orphan_images"] for r in results),
        "image_cue_questions": sum(r["image_cue_questions"] for r in results),
        "in_merged": sum(1 for it in all_items if it.get("in_merged") and it.get("images")),
        "out_dir": str(OUT_IMG.relative_to(ROOT)),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "review": str(REVIEW.relative_to(ROOT)),
        "note": "2021 scanned PDF skipped; watermarks filtered",
    }
    MANIFEST.write_text(
        json.dumps({"summary": summary, "pdfs": results, "items": all_items}, ensure_ascii=False, indent=2),
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
