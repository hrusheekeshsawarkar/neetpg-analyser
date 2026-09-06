#!/usr/bin/env python3
"""
Extract clinical images from neetfmgeplans PDFs.

Targets:
  - NEETPG-20XX.pdf          (PrepLadder layout → source neetfmgeplans)
  - NEETPG-yearwise.pdf      (MEDINK 2-col → source neetfmgeplans-yearwise)

Usage:
  python analysis/extract_images_fmgeplans.py --per-year 2022-2024
  python analysis/extract_images_fmgeplans.py --yearwise
  python analysis/extract_images_fmgeplans.py --all --patch-merged
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

PDF_DIR = ROOT / "neet-pg-papers" / "neetfmgeplans"
DATA = ROOT / "analysis" / "data"
MERGED = DATA / "merged_questions.json"
OUT_IMG = DATA / "question_images" / "fmgeplans"
MANIFEST = DATA / "image_extract_fmgeplans.json"
REVIEW = ROOT / "analysis" / "reports" / "image_extract_fmgeplans_review.html"

YEAR_HDR_RE = re.compile(r"EXAMINATION PAPER\s+(20\d{2})", re.I)
SOLUTION_RE = re.compile(r"SOLUTION", re.I)
NUM_Q_RE = re.compile(r"^\s*(\d{1,3})\.\s+(?=[A-Za-z(\[])")


def parse_years(spec: str) -> list[int]:
    return cd.parse_years(spec)


def is_clinical_image(width: int, height: int, display: fitz.Rect) -> bool:
    if not cd.is_clinical_image(width, height, display):
        return False
    # PrepLadder / MEDINK top banners
    if width >= 1500 and height < 800 and (max(width, height) / max(1, min(width, height))) > 2.0:
        return False
    if display.y0 < 70 and display.height < 80 and display.width > 300:
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
                "xc": float((bbox.x0 + bbox.x1) / 2),
            }
        )
    out.sort(key=lambda d: (d["y0"], d["xc"]))
    return out


def page_year(page: fitz.Page, fallback: int | None = None) -> int | None:
    text = page.get_text() or ""
    m = YEAR_HDR_RE.search(text)
    if m:
        return int(m.group(1))
    return fallback


def is_solution_page(page: fitz.Page) -> bool:
    head = (page.get_text() or "")[:400]
    return bool(SOLUTION_RE.search(head)) and "EXAMINATION PAPER" in head.upper()


def page_question_starts_numbered(page: fitz.Page) -> list[tuple[int, float, float, str]]:
    """Return [(qnum, y0, x0, snippet), ...] for MEDINK 'N. stem' layout."""
    starts = []
    seen = []
    for block in page.get_text("blocks"):
        raw = (block[4] or "").strip()
        if not raw:
            continue
        m = NUM_Q_RE.match(raw)
        if not m:
            continue
        qnum = int(m.group(1))
        if qnum < 1 or qnum > 400:
            continue
        y0 = float(block[1])
        x0 = float(block[0])
        if any(abs(y0 - sy) < 8 and abs(x0 - sx) < 40 for sy, sx in seen):
            continue
        starts.append((qnum, y0, x0, re.sub(r"\s+", " ", raw)[:160]))
        seen.append((y0, x0))
    starts.sort(key=lambda t: (t[2] > 250, t[1]))  # left col then right, by y
    return starts


def same_column(q_x: float, im_xc: float, page_w: float) -> bool:
    mid = page_w / 2
    q_left = q_x < mid - 20
    im_left = im_xc < mid
    return q_left == im_left


def load_merged_index() -> dict[tuple[str, int, str], list[dict]]:
    if not MERGED.exists():
        return {}
    rows = json.loads(MERGED.read_text())
    idx: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for row in rows:
        src = row.get("source") or ""
        if not src.startswith("neetfmgeplans"):
            continue
        year = row.get("year")
        qn = str(row.get("question_number") or "").strip()
        if year is None or not qn:
            continue
        idx[(src, int(year), qn)].append(row)
    return idx


def _match_row(merged_idx, source: str, year: int | None, qnum: int, qtext: str, snippet: str):
    row = None
    if year is not None:
        cands = merged_idx.get((source, year, str(qnum)), [])
        row = cands[0] if cands else None
    qid = cd.make_qid(row) if row else None
    if not qid:
        stem = cd.normalize_stem(qtext or snippet)[:200]
        qid = hashlib.sha256(f"{year}|{source}|{qnum}|{stem}".encode()).hexdigest()
    return row, qid


def process_prepladder_pdf(path: Path, year: int, merged_idx: dict) -> dict:
    """Same PrepLadder pairing as Nishant."""
    spec = {
        "path": path,
        "year": year,
        "exam": "NEET PG",
        "source": "neetfmgeplans",
        "shift": None,
        "label": path.stem,
    }
    # Temporarily point nishant OUT to fmgeplans subdir by processing inline
    # Reuse nishant process but override source/out — easier to duplicate thin wrapper:
    return _process_generic_prepladder(spec, merged_idx)


def _process_generic_prepladder(spec: dict, merged_idx: dict) -> dict:
    path: Path = spec["path"]
    year = spec["year"]
    source = spec["source"]
    result = {
        "year": year,
        "source": source,
        "label": spec["label"],
        "pdf": str(path.relative_to(ROOT)),
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
    pages_data = []
    for page_i in range(len(doc)):
        page = doc[page_i]
        starts = ns.page_question_starts(page)
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
            row, qid = _match_row(merged_idx, source, year, qnum, qtext, snippet)
            item = {
                "year": year,
                "source": source,
                "label": spec["label"],
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
            cands = [it for it in page_items if q_y.get(it["_qnum"], 0) <= im["yc"]]
            if not cands and carry_item:
                target = carry_item
            elif cands:
                target = max(cands, key=lambda it: q_y.get(it["_qnum"], 0))
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


def question_text_in_column(
    page: fitz.Page, y0: float, y1: float, x0: float, page_w: float
) -> str:
    """Collect text in [y0, y1) that sits in the same half-page column as x0."""
    mid = page_w / 2
    want_left = x0 < mid - 20
    parts = []
    for block in page.get_text("blocks"):
        by0, by1 = float(block[1]), float(block[3])
        bx0 = float(block[0])
        if by1 < y0 - 2 or by0 >= y1 - 0.5:
            continue
        block_left = bx0 < mid - 20
        if block_left != want_left:
            continue
        parts.append(block[4] or "")
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def stem_only(text: str, snippet: str = "") -> str:
    """Prefer the MCQ stem; drop Ans / long explanations."""
    t = text or snippet or ""
    # cut at answer key
    t = re.split(r"\bAns\s*:", t, maxsplit=1, flags=re.I)[0]
    # if options present, keep through option block start only once
    m = re.search(r"\([A-Da-d1-4]\)", t)
    if m:
        # keep stem + options (up to ~4 options worth), drop trailing prose
        after = t[m.start() :]
        # stop if explanation-like sentence after options
        after = re.split(r"(?<=\))\s+(?=[A-Z][a-z]+ (?:is|are|shows|displays|provided))", after, maxsplit=1)[0]
        t = t[: m.start()] + after
    t = re.sub(r"\s+", " ", t).strip()
    return t[:400]


def stem_has_image_cue(snippet: str, stem: str) -> bool:
    """Cue must appear in the stem line / stem body — not only in Ans explanations."""
    head = f"{snippet or ''} {stem or ''}"
    # strip anything after Ans if still present
    head = re.split(r"\bAns\s*:", head, maxsplit=1, flags=re.I)[0]
    # ignore option letters region for cue? keep — "shown in the image" is usually in stem
    return bool(cd.IMAGE_CUE_RE.search(head) or cd.has_image_ref(head))


def is_yearwise_exam_page(page: fitz.Page) -> bool:
    """Keep Examination Paper pages; drop pure solution dumps."""
    text = page.get_text() or ""
    head = text[:500]
    if re.search(r"Examination\s+Paper\s+20\d{2}", head, re.I):
        return True
    # Count numbered stems anywhere on the page (need MULTILINE)
    q_hits = len(re.findall(r"(?m)^\s*\d{1,3}\.\s+(?=[A-Za-z(\[])", text))
    if q_hits >= 2 and re.search(r"\([A-D]\)", text):
        # Reject "286. (A) Answer prose…" solution dumps
        sol_hits = len(re.findall(r"(?m)^\s*\d{1,3}\.\s*\([A-D]\)\s+\S+", text))
        if sol_hits / max(q_hits, 1) > 0.6:
            return False
        return True
    return False


def process_yearwise(path: Path, merged_idx: dict, limit_pages: int = 0) -> dict:
    source = "neetfmgeplans-yearwise"
    result = {
        "year": None,
        "source": source,
        "label": path.stem,
        "pdf": str(path.relative_to(ROOT)),
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
    out_dir = OUT_IMG / path.stem
    if out_dir.exists():
        for p in out_dir.glob("*"):
            if p.is_file():
                p.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(path)
    n_pages = len(doc) if not limit_pages else min(len(doc), limit_pages)
    result["pages"] = n_pages
    current_year: int | None = None
    # carry: unanswered image-cue stem waiting for top-of-next-page figure (same column)
    carry_item = None

    for page_i in range(n_pages):
        page = doc[page_i]
        current_year = page_year(page, current_year)
        if is_solution_page(page) or not is_yearwise_exam_page(page):
            carry_item = None
            continue

        starts = page_question_starts_numbered(page)
        images = page_clinical_images(page)
        result["clinical_images_found"] += len(images)
        result["questions_detected"] += len(starts)
        page_w = float(page.rect.width)
        page_h = float(page.rect.height)
        assigned: set[int] = set()

        # Leading same-column images → prior page carry (stem already had cue)
        if carry_item and images:
            first_y_left = min((y for _, y, x, _ in starts if x < page_w / 2), default=page_h)
            first_y_right = min((y for _, y, x, _ in starts if x >= page_w / 2), default=page_h)
            cx = carry_item.get("_x0", 0)
            first_y = first_y_left if cx < page_w / 2 else first_y_right
            leading = [
                (ii, im)
                for ii, im in enumerate(images)
                if im["yc"] < first_y - 5 and same_column(cx, im["xc"], page_w)
            ]
            if leading:
                saved = cd._save_images(doc, out_dir, carry_item["_qnum"], page_i, leading, result)
                if saved:
                    carry_item["images"].extend(saved)
                    for ii, _ in leading:
                        assigned.add(ii)
                    carry_item["status"] = (
                        "linked" if carry_item.get("in_merged") else "linked_no_merge_row"
                    )
                    carry_item = None

        left = [(q, y, x, s) for q, y, x, s in starts if x < page_w / 2]
        right = [(q, y, x, s) for q, y, x, s in starts if x >= page_w / 2]
        page_items = []

        for col in (left, right):
            for qi, (qnum, y0, x0, snippet) in enumerate(col):
                y1 = col[qi + 1][1] if qi + 1 < len(col) else page_h
                raw = question_text_in_column(page, y0, y1, x0, page_w)
                stem = stem_only(raw, snippet)
                cue = stem_has_image_cue(snippet, stem)
                if cue:
                    result["image_cue_questions"] += 1

                band = []
                for ii, im in enumerate(images):
                    if ii in assigned:
                        continue
                    if not same_column(x0, im["xc"], page_w):
                        continue
                    # Image must sit below stem start and above next stem in this column
                    if im["yc"] >= y0 - 5 and im["y0"] < y1 - 5:
                        band.append((ii, im))

                # Strict: only emit if stem cues an image OR a figure sits in-band
                if not band and not cue:
                    continue

                saved = cd._save_images(doc, out_dir, qnum, page_i, band, result) if band else []
                for ii, _ in band:
                    assigned.add(ii)

                # If we have a figure but stem has no cue, still keep (figure is strong signal)
                # If cue but no figure, keep as cue_unlinked for review
                year = current_year
                row, qid = _match_row(merged_idx, source, year, qnum, stem, snippet)
                display = stem if stem else snippet
                # Prefer merge stem when available and non-empty
                merge_stem = (row or {}).get("question_text") or ""
                item = {
                    "year": year,
                    "source": source,
                    "label": path.stem,
                    "page": page_i + 1,
                    "question_number": str(qnum),
                    "qid": qid,
                    "status": "linked" if (saved and row) else (
                        "linked_no_merge_row" if saved else "cue_unlinked"
                    ),
                    "in_merged": bool(row),
                    "has_image_cue": cue,
                    "ask_type": (row or {}).get("ask_type"),
                    "subject": (row or {}).get("subject_clean") or (row or {}).get("subject"),
                    "question_preview": display[:220],
                    "question_text": merge_stem[:400] if merge_stem else display[:400],
                    "images": saved,
                    "_qnum": qnum,
                    "_x0": x0,
                    "_y0": y0,
                    "_cue": cue,
                }
                page_items.append(item)

        # Orphans: ONLY attach to same-column stems that already have an image cue
        # and still lack a figure (never dump random figures onto landfill / stats Qs)
        for ii, im in enumerate(images):
            if ii in assigned:
                continue
            cands = [
                it
                for it in page_items
                if it.get("_cue")
                and not it["images"]
                and same_column(it["_x0"], im["xc"], page_w)
                and it["_y0"] <= im["yc"]
            ]
            if not cands:
                result["orphan_images"] += 1
                continue
            target = max(cands, key=lambda it: it["_y0"])
            # require image reasonably close under the stem (not half a page away past other Qs)
            if im["y0"] - target["_y0"] > 280:
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
            needy = [
                it
                for it in page_items
                if not it["images"] and it.get("_cue") and it["_y0"] > page_h * 0.55
            ]
            if needy:
                carry_item = max(needy, key=lambda it: it["_y0"])

    for it in result["items"]:
        for k in ("_qnum", "_x0", "_y0", "_cue"):
            it.pop(k, None)
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
        payload = {
            "images": [im["path"] for im in it["images"]],
            "image_status": "linked",
            "image_source": it.get("source") or "neetfmgeplans",
        }
        if it.get("qid"):
            by_qid[it["qid"]] = payload
        if it.get("year") is not None:
            by_key[(it.get("source"), it["year"], str(it["question_number"]))] = payload

    n = 0
    for row in rows:
        src = row.get("source") or ""
        if not src.startswith("neetfmgeplans"):
            continue
        if row.get("images") and row.get("image_source") not in {None, "", src}:
            # keep collegedunia/nishant if already better
            if row.get("image_source") in {"collegedunia", "nishant-aipgmee", "nishant-neetpg"}:
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
        "fmgeplans image extraction — review",
    ).replace("CollegeDunia image extract review", "fmgeplans image extract review")
    REVIEW.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-year", default="", help="Years for NEETPG-20XX.pdf e.g. 2022-2024")
    ap.add_argument("--yearwise", action="store_true", help="Process NEETPG-yearwise.pdf")
    ap.add_argument("--all", action="store_true", help="Per-year 2022-2025 + yearwise")
    ap.add_argument("--limit-pages", type=int, default=0, help="Yearwise page cap (smoke)")
    ap.add_argument("--patch-merged", action="store_true")
    args = ap.parse_args()

    if args.all:
        per_years = list(range(2022, 2026))
        do_yearwise = True
    else:
        per_years = parse_years(args.per_year) if args.per_year else []
        do_yearwise = args.yearwise
    if not per_years and not do_yearwise:
        per_years = list(range(2022, 2025))
        do_yearwise = True

    merged_idx = load_merged_index()
    print(f"fmgeplans image extract — merged keys={len(merged_idx)}")

    results = []
    all_items: list[dict] = []

    for year in per_years:
        path = PDF_DIR / f"NEETPG-{year}.pdf"
        if not path.exists():
            print(f"  skip missing {path.name}")
            continue
        # Huge 2023 file is still PrepLadder text+images (ok)
        print(f"\n=== {path.name} ===")
        r = process_prepladder_pdf(path, year, merged_idx)
        results.append(r)
        all_items.extend(r["items"])
        print(
            f"  pages={r['pages']} clinical={r['clinical_images_found']} "
            f"qs={r['questions_detected']} cues={r['image_cue_questions']} "
            f"linked={r['linked']} cue_unlinked={r['cue_unlinked']} orphans={r['orphan_images']}"
        )

    if do_yearwise:
        path = PDF_DIR / "NEETPG-yearwise.pdf"
        if path.exists():
            print(f"\n=== {path.name} ===")
            r = process_yearwise(path, merged_idx, limit_pages=args.limit_pages)
            results.append(r)
            all_items.extend(r["items"])
            print(
                f"  pages={r['pages']} clinical={r['clinical_images_found']} "
                f"qs={r['questions_detected']} cues={r['image_cue_questions']} "
                f"linked={r['linked']} cue_unlinked={r['cue_unlinked']} orphans={r['orphan_images']}"
            )

    summary = {
        "years": per_years,
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
