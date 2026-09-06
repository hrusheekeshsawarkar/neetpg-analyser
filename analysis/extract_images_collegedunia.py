#!/usr/bin/env python3
"""
Extract clinical images from CollegeDunia NEET PG PDFs and link them to questions.

Pilot approach:
  1. Parse each page for numbered question stems (Y positions)
  2. Collect clinical-sized embedded images (drop logos / banners / stamps)
  3. Assign images whose vertical span falls inside a question's Y range
  4. Match to merged_questions by (source=collegedunia, year, question_number)
  5. Write image files + JSON manifest + HTML review

Usage:
  python analysis/extract_images_collegedunia.py --years 2022
  python analysis/extract_images_collegedunia.py --years 2016-2024
  python analysis/extract_images_collegedunia.py --years 2022 --patch-merged
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "neet-pg-papers" / "collegedunia"
DATA = ROOT / "analysis" / "data"
MERGED = DATA / "merged_questions.json"
OUT_IMG = DATA / "question_images" / "collegedunia"
MANIFEST = DATA / "image_extract_collegedunia.json"
REVIEW = ROOT / "analysis" / "reports" / "image_extract_collegedunia_review.html"

# Question starts at left-ish margin: "1 The structure..." or "1. Which..." or "10)"
QSTART_RE = re.compile(
    r"(?m)^\s*(\d{1,3})(?:[\.\)])?(?:\s+|$)(?=[A-Za-z(\[])"
)
IMAGE_CUE_RE = re.compile(
    r"(?i)("
    r"image\s+below|figure\s+below|histology\s+image|photograph|"
    r"shown\s+(below|in\s+the\s+image|in\s+the\s+figure)|"
    r"given\s+(below|image|structure|x-?ray)|"
    r"in\s+the\s+(image|figure|diagram)|following\s+(image|figure|x-?ray)|"
    r"marked\s+[A-D]|identify\s+the\s+(given|type|structure|image|lesion|organism|mask)|"
    r"\bx-?ray\b|\becg\b|\bugie\b|\bfundoscopy\b|"
    r"device\s+shown|finding\s+shown|maneuver\s+shown|fixation\s+shown|"
    r"specimen.{0,40}shown|as\s+shown\s+below|image\s+is\s+given|image\s+shown"
    r")"
)
IMAGE_REF_RE = re.compile(
    r"\b(image\s+below|figure\s+below|shown\s+in\s+the\s+(figure|image|x-?ray)|"
    r"marked\s+[A-D]|given\s+(x-?ray|image|figure)|photograph\s+below|"
    r"in\s+the\s+diagram|following\s+(image|figure|x-?ray))\b",
    re.I,
)


def normalize_stem(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def make_qid(row: dict) -> str:
    stem = normalize_stem(row.get("question_text") or "")[:200]
    raw = "|".join(
        [
            str(row.get("year") or ""),
            str(row.get("exam") or ""),
            str(row.get("shift") or ""),
            str(row.get("question_number") or ""),
            stem,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def has_image_ref(text: str) -> bool:
    return bool(IMAGE_REF_RE.search(text or ""))


def parse_years(spec: str) -> list[int]:
    years: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            years.extend(range(int(a), int(b) + 1))
        else:
            years.append(int(part))
    return sorted(set(years))


def is_clinical_image(width: int, height: int, display: fitz.Rect) -> bool:
    """Filter logos, watermarks, page banners, tiny stamps."""
    if width < 90 or height < 90:
        return False
    if display.width < 40 or display.height < 30:
        return False
    aspect = max(width, height) / max(1, min(width, height))
    # Wide header/footer banners
    if width >= 1000 and height < 750 and aspect > 2.2:
        return False
    if display.width > 350 and display.height < 55 and aspect > 3.5:
        return False
    # Tiny corner logos (CollegeDunia stamp often ~50–80 display height at edges)
    if display.y0 > 750 and display.height < 40:
        return False
    return True


def page_question_starts(page: fitz.Page) -> list[tuple[int, float, str]]:
    """Return [(qnum, y0, stem_snippet), ...] ordered by Y."""
    text = page.get_text() or ""
    # Prefer line-based detection for reliable numbering
    starts: list[tuple[int, float, str]] = []
    seen_y: list[float] = []
    for block in page.get_text("blocks"):
        raw = block[4] or ""
        y0 = float(block[1])
        # Only consider left-column question headers (x0 typically < 120 for CD)
        if float(block[0]) > 160:
            continue
        m = QSTART_RE.match(raw.strip()) if raw.strip() else None
        if not m:
            # sometimes number is alone in first line of multi-line block
            first = raw.split("\n", 1)[0].strip()
            m = QSTART_RE.match(first)
        if not m:
            continue
        qnum = int(m.group(1))
        if qnum < 1 or qnum > 300:
            continue
        # de-dupe near-identical Y (split lines of same Q)
        if any(abs(y0 - sy) < 8 for sy in seen_y):
            continue
        snippet = re.sub(r"\s+", " ", raw).strip()[:160]
        starts.append((qnum, y0, snippet))
        seen_y.append(y0)

    # Fallback: search full page text positions via search_for for "N "
    if len(starts) < 2:
        starts = []
        for m in QSTART_RE.finditer(text):
            qnum = int(m.group(1))
            if qnum < 1 or qnum > 300:
                continue
            needle = m.group(0).strip()[:12]
            rects = page.search_for(needle)
            if not rects:
                continue
            y0 = float(rects[0].y0)
            if any(abs(y0 - sy) < 8 for _, sy, _ in starts):
                continue
            starts.append((qnum, y0, needle))

    starts.sort(key=lambda t: t[1])
    return starts


def page_clinical_images(page: fitz.Page, doc: fitz.Document) -> list[dict]:
    out = []
    for info in page.get_image_info(xrefs=True):
        w, h = int(info.get("width") or 0), int(info.get("height") or 0)
        bbox = fitz.Rect(info["bbox"])
        if not is_clinical_image(w, h, bbox):
            continue
        xref = info.get("xref")
        out.append(
            {
                "xref": xref,
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


def question_text_in_range(page: fitz.Page, y0: float, y1: float) -> str:
    """Text with block top in [y0, y1) so the next question header is excluded."""
    parts = []
    for block in page.get_text("blocks"):
        by0, by1 = float(block[1]), float(block[3])
        if by1 < y0 - 2 or by0 >= y1 - 0.5:
            continue
        parts.append(block[4] or "")
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def export_image(doc: fitz.Document, xref: int, dest: Path) -> dict:
    """Write image bytes; convert uncommon formats to png via pixmap if needed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        info = doc.extract_image(xref)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    ext = (info.get("ext") or "png").lower()
    data = info.get("image") or b""
    if not data:
        return {"ok": False, "error": "empty"}
    if ext in {"jpg", "jpeg", "png", "webp"}:
        out_ext = "jpg" if ext in {"jpg", "jpeg"} else ext
        path = dest.with_suffix(f".{out_ext}")
        path.write_bytes(data)
        return {
            "ok": True,
            "path": path,
            "ext": out_ext,
            "width": info.get("width"),
            "height": info.get("height"),
            "bytes": len(data),
        }
    # fallback render
    try:
        pix = fitz.Pixmap(doc, xref)
        if pix.n > 4:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        path = dest.with_suffix(".png")
        pix.save(path)
        return {
            "ok": True,
            "path": path,
            "ext": "png",
            "width": pix.width,
            "height": pix.height,
            "bytes": path.stat().st_size,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def load_merged_index() -> dict[tuple[int, str], list[dict]]:
    """(year, question_number) -> list of collegedunia rows."""
    if not MERGED.exists():
        return {}
    rows = json.loads(MERGED.read_text())
    idx: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("source") != "collegedunia":
            continue
        year = row.get("year")
        qn = str(row.get("question_number") or "").strip()
        if year is None or not qn:
            continue
        idx[(int(year), qn)].append(row)
    return idx


def _build_item(
    *,
    year: int,
    page_i: int,
    qnum: int,
    qtext: str,
    snippet: str,
    cue: bool,
    merged_idx: dict,
    images_meta: list[dict],
) -> dict:
    candidates = merged_idx.get((year, str(qnum)), [])
    row = candidates[0] if candidates else None
    qid = make_qid(row) if row else None
    if not qid:
        stem = normalize_stem(qtext or snippet)[:200]
        qid = hashlib.sha256(f"{year}|collegedunia|{qnum}|{stem}".encode()).hexdigest()
    status = "linked" if (images_meta and row) else (
        "linked_no_merge_row" if images_meta else "cue_unlinked"
    )
    return {
        "year": year,
        "page": page_i + 1,
        "question_number": str(qnum),
        "qid": qid,
        "status": status,
        "in_merged": bool(row),
        "has_image_cue": cue or has_image_ref(qtext),
        "ask_type": (row or {}).get("ask_type"),
        "subject": (row or {}).get("subject_clean") or (row or {}).get("subject"),
        "question_preview": (qtext or snippet)[:220],
        "question_text": (row or {}).get("question_text") or (qtext or "")[:400],
        "images": images_meta,
        "_qnum": qnum,
        "_page_i": page_i,
    }


def _save_images(
    doc: fitz.Document,
    year_dir: Path,
    qnum: int,
    page_i: int,
    band_imgs: list[tuple[int, dict]],
    result: dict,
) -> list[dict]:
    saved = []
    for ord_i, (_ii, im) in enumerate(band_imgs):
        dest = year_dir / f"q{qnum:03d}_p{page_i+1:03d}_{ord_i}"
        exp = export_image(doc, im["xref"], dest)
        if not exp.get("ok"):
            result["errors"].append(
                f"year={year_dir.name} p{page_i+1} q{qnum} xref={im['xref']}: {exp.get('error')}"
            )
            continue
        rel = str(exp["path"].relative_to(DATA))
        saved.append(
            {
                "path": rel,
                "width": exp.get("width") or im["width"],
                "height": exp.get("height") or im["height"],
                "bytes": exp.get("bytes"),
                "bbox": im["bbox"],
                "xref": im["xref"],
            }
        )
    return saved


def process_year(year: int, merged_idx: dict) -> dict:
    pdf_path = PDF_DIR / f"neetpg-{year}.pdf"
    result = {
        "year": year,
        "pdf": str(pdf_path.relative_to(ROOT)) if pdf_path.exists() else None,
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
    if not pdf_path.exists():
        result["errors"].append(f"missing PDF: {pdf_path}")
        return result

    # Clean prior exports for this year so re-runs are deterministic
    year_dir = OUT_IMG / str(year)
    if year_dir.exists():
        for p in year_dir.glob("*"):
            if p.is_file():
                p.unlink()
    year_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    result["pages"] = len(doc)

    # Pass 1: collect page structures
    pages_data = []
    for page_i in range(len(doc)):
        page = doc[page_i]
        starts = page_question_starts(page)
        images = page_clinical_images(page, doc)
        result["clinical_images_found"] += len(images)
        result["questions_detected"] += len(starts)
        pages_data.append({"starts": starts, "images": images, "page": page})

    # Pass 2: assign images. Carry questions that end a page without an image yet.
    carry_item: dict | None = None
    items_by_key: dict[tuple[int, int], dict] = {}  # (page_i, qnum) -> item

    for page_i, pdata in enumerate(pages_data):
        page = pdata["page"]
        starts = pdata["starts"]
        images = pdata["images"]
        page_h = float(page.rect.height)
        assigned: set[int] = set()
        first_q_y = starts[0][1] if starts else page_h

        # Leading images (above first question) → previous page carry
        leading = [
            (ii, im)
            for ii, im in enumerate(images)
            if im["y1"] <= first_q_y + 10 or (im["y0"] < first_q_y - 20)
        ]
        # stricter: image mostly above first question
        leading = [(ii, im) for ii, im in enumerate(images) if im["yc"] < first_q_y - 5]

        if carry_item and leading:
            saved = _save_images(doc, year_dir, carry_item["_qnum"], page_i, leading, result)
            if saved:
                carry_item["images"].extend(saved)
                for ii, _ in leading:
                    assigned.add(ii)
                carry_item["status"] = (
                    "linked" if carry_item.get("in_merged") else "linked_no_merge_row"
                )
                carry_item = None

        page_items: list[dict] = []
        for qi, (qnum, y0, snippet) in enumerate(starts):
            y1 = starts[qi + 1][1] if qi + 1 < len(starts) else page_h
            qtext = question_text_in_range(page, y0, y1)
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

            saved = _save_images(doc, year_dir, qnum, page_i, band, result) if band else []
            for ii, _ in band:
                assigned.add(ii)

            item = _build_item(
                year=year,
                page_i=page_i,
                qnum=qnum,
                qtext=qtext,
                snippet=snippet,
                cue=cue,
                merged_idx=merged_idx,
                images_meta=saved,
            )
            page_items.append(item)
            items_by_key[(page_i, qnum)] = item

        # Remaining orphans: attach to nearest question above on this page
        for ii, im in enumerate(images):
            if ii in assigned:
                continue
            q_y = {qnum: y0 for qnum, y0, _ in starts}
            candidates = [
                it
                for it in page_items
                if q_y.get(it["_qnum"], 0) <= im["yc"]
            ]
            if not candidates and carry_item:
                target = carry_item
            elif candidates:
                target = max(candidates, key=lambda it: q_y.get(it["_qnum"], 0))
            else:
                result["orphan_images"] += 1
                continue
            saved = _save_images(doc, year_dir, target["_qnum"], page_i, [(ii, im)], result)
            if saved:
                target["images"].extend(saved)
                assigned.add(ii)
                target["status"] = (
                    "linked" if target.get("in_merged") else "linked_no_merge_row"
                )
                # if we filled carry, clear it
                if target is carry_item and target["images"]:
                    carry_item = None
            else:
                result["orphan_images"] += 1

        for it in page_items:
            if it["images"]:
                result["linked"] += 1
            elif it.get("has_image_cue"):
                result["cue_unlinked"] += 1
            result["items"].append(it)

        # Carry last cue-without-image (or last question near page bottom) to next page
        carry_item = None
        if page_items:
            last = page_items[-1]
            last_y = next((y0 for qn, y0, _ in starts if qn == last["_qnum"]), 0)
            near_bottom = last_y > page_h * 0.55
            if not last["images"] and (last.get("has_image_cue") or near_bottom):
                # only carry if cue — avoid attaching random top images to plain stems
                if last.get("has_image_cue"):
                    carry_item = last

    # Drop internal keys from items
    for it in result["items"]:
        it.pop("_qnum", None)
        it.pop("_page_i", None)

    # Recompute linked / cue_unlinked after carry fills
    result["linked"] = sum(1 for it in result["items"] if it.get("images"))
    result["cue_unlinked"] = sum(
        1 for it in result["items"] if not it.get("images") and it.get("has_image_cue")
    )
    for it in result["items"]:
        if it.get("images"):
            it["status"] = "linked" if it.get("in_merged") else "linked_no_merge_row"
        elif it.get("has_image_cue"):
            it["status"] = "cue_unlinked"

    doc.close()
    return result


def write_review_html(all_items: list[dict], summary: dict) -> None:
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    # Prefer linked cue items first, then unlinked (easier QA)
    ordered = sorted(
        all_items,
        key=lambda it: (
            0 if it.get("status") == "cue_unlinked" else 1,
            it.get("year") or 0,
            int(it.get("question_number") or 0),
        ),
    )
    rows_html = []
    for it in ordered:
        imgs = it.get("images") or []
        thumbs = []
        for im in imgs:
            rel = f"../data/{im['path']}"
            thumbs.append(
                f'<div class="thumb"><img src="{rel}" alt="q{it["question_number"]}" loading="lazy"/>'
                f'<div class="meta">{im["width"]}×{im["height"]}</div></div>'
            )
        status = it.get("status", "")
        cls = "ok" if status.startswith("linked") else "bad"
        qtxt = (it.get("question_text") or it.get("question_preview") or "").replace("<", "&lt;")
        rows_html.append(
            f"""
            <article class="card {cls}">
              <header>
                <strong>{it.get('year')} Q{it.get('question_number')}</strong>
                <span class="badge">{status}</span>
                <span class="muted">p{it.get('page')} · {it.get('subject') or '—'} · {it.get('ask_type') or '—'}</span>
              </header>
              <p>{qtxt}</p>
              <div class="thumbs">{''.join(thumbs) or '<em>no image</em>'}</div>
            </article>
            """
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>CollegeDunia image extract review</title>
  <style>
    :root {{ font-family: ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 24px; background: #f6f7f9; color: #1a1a1a; }}
    h1 {{ font-size: 1.35rem; }}
    .summary {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0 24px; }}
    .summary div {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 10px 14px; }}
    .card {{ background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 14px 16px; margin-bottom: 14px; }}
    .card.bad {{ border-color: #e5a0a0; background: #fff8f8; }}
    .card.ok {{ border-color: #b7d7c2; }}
    header {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: baseline; margin-bottom: 8px; }}
    .badge {{ font-size: 12px; background: #eee; border-radius: 4px; padding: 2px 6px; }}
    .muted {{ color: #666; font-size: 12px; }}
    .thumbs {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 10px; }}
    .thumb img {{ max-height: 180px; max-width: 280px; border: 1px solid #ccc; border-radius: 4px; }}
    .thumb .meta {{ font-size: 11px; color: #666; }}
    p {{ margin: 0; line-height: 1.45; font-size: 14px; }}
    .note {{ color: #444; font-size: 13px; margin-bottom: 18px; }}
  </style>
</head>
<body>
  <h1>CollegeDunia image extraction — review</h1>
  <p class="note">Open this file via a local static server or file:// from the repo so
  <code>../data/question_images/...</code> resolves. Cue-unlinked cards are listed first.</p>
  <div class="summary">
    <div><strong>Years</strong><br/>{summary.get('years')}</div>
    <div><strong>Linked</strong><br/>{summary.get('linked')}</div>
    <div><strong>Cue unlinked</strong><br/>{summary.get('cue_unlinked')}</div>
    <div><strong>Clinical imgs seen</strong><br/>{summary.get('clinical_images_found')}</div>
    <div><strong>Orphan imgs</strong><br/>{summary.get('orphan_images')}</div>
    <div><strong>Matched merge rows</strong><br/>{summary.get('in_merged')}</div>
  </div>
  {''.join(rows_html)}
</body>
</html>
"""
    REVIEW.write_text(html, encoding="utf-8")


def patch_merged(items: list[dict]) -> int:
    """Attach images[] + image_status onto matching merged_questions rows."""
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
            "image_source": "collegedunia",
        }
        if it.get("qid"):
            by_qid[it["qid"]] = payload
        by_key[(it["year"], str(it["question_number"]))] = payload

    n = 0
    for row in rows:
        if row.get("source") != "collegedunia":
            continue
        qid = make_qid(row)
        payload = by_qid.get(qid) or by_key.get((row.get("year"), str(row.get("question_number") or "")))
        if not payload:
            continue
        row.update(payload)
        n += 1
    MERGED.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", default="2022", help="e.g. 2022 or 2016-2024 or 2020,2022,2024")
    ap.add_argument("--patch-merged", action="store_true", help="Write images[] into merged_questions.json")
    ap.add_argument("--limit-items-review", type=int, default=0, help="Cap review HTML items (0=all)")
    args = ap.parse_args()

    years = parse_years(args.years)
    # Prefer years that actually have PDFs with figures
    merged_idx = load_merged_index()
    print(f"CollegeDunia image extract — years={years}")
    print(f"Merged collegedunia index keys: {len(merged_idx)}")

    year_results = []
    all_items: list[dict] = []
    for year in years:
        print(f"\n=== {year} ===")
        r = process_year(year, merged_idx)
        year_results.append(r)
        all_items.extend(r["items"])
        print(
            f"  pages={r['pages']} clinical={r['clinical_images_found']} "
            f"qs={r['questions_detected']} cues={r['image_cue_questions']} "
            f"linked={r['linked']} cue_unlinked={r['cue_unlinked']} orphans={r['orphan_images']}"
        )
        if r["errors"][:3]:
            print("  errors:", r["errors"][:3])

    summary = {
        "years": years,
        "linked": sum(r["linked"] for r in year_results),
        "cue_unlinked": sum(r["cue_unlinked"] for r in year_results),
        "clinical_images_found": sum(r["clinical_images_found"] for r in year_results),
        "orphan_images": sum(r["orphan_images"] for r in year_results),
        "image_cue_questions": sum(r["image_cue_questions"] for r in year_results),
        "in_merged": sum(1 for it in all_items if it.get("in_merged") and it.get("images")),
        "out_dir": str(OUT_IMG.relative_to(ROOT)),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "review": str(REVIEW.relative_to(ROOT)),
    }

    manifest = {
        "summary": summary,
        "years": year_results,
        "items": all_items,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    review_items = all_items
    if args.limit_items_review and args.limit_items_review > 0:
        review_items = all_items[: args.limit_items_review]
    write_review_html(review_items, summary)

    patched = 0
    if args.patch_merged:
        patched = patch_merged([it for it in all_items if it.get("images")])
        print(f"\nPatched merged_questions.json rows: {patched}")

    print("\n=== DONE ===")
    print(json.dumps(summary, indent=2))
    print(f"Review: {REVIEW}")


if __name__ == "__main__":
    main()
