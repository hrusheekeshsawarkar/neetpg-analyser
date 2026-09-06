#!/usr/bin/env python3
"""
Seed Supabase from offline analysis artifacts.

Requires:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY

Usage:
  python analysis/sync/seed_supabase.py
  python analysis/sync/seed_supabase.py --skip-questions
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "analysis"
DATA = ANALYSIS / "data"
REPORTS = ANALYSIS / "reports"
PLOTS = ANALYSIS / "plots"

IMAGE_RE = re.compile(
    r"\b(image\s+below|figure\s+below|shown\s+in\s+the\s+(figure|image|x-?ray)|"
    r"marked\s+[A-D]|given\s+(x-?ray|image|figure)|photograph\s+below|"
    r"in\s+the\s+diagram|following\s+(image|figure|x-?ray))\b",
    re.I,
)


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


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
    return bool(IMAGE_RE.search(text or ""))


def get_client():
    try:
        from supabase import create_client
    except ImportError:
        print("Install: pip install supabase", file=sys.stderr)
        raise
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit(
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (service role for upserts)."
        )
    return create_client(url, key)


def chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def upsert_questions(client, path: Path) -> int:
    rows = json.loads(path.read_text())
    payload = []
    for row in rows:
        qtext = row.get("question_text") or ""
        payload.append(
            {
                "qid": make_qid(row),
                "question_number": str(row.get("question_number") or "") or None,
                "year": row.get("year"),
                "exam": row.get("exam"),
                "shift": str(row.get("shift") or "") or None,
                "source": row.get("source"),
                "subject": row.get("subject"),
                "subject_clean": row.get("subject_clean") or row.get("subject"),
                "topic": row.get("topic"),
                "topic_clean": row.get("topic_clean") or row.get("topic"),
                "topics": row.get("topics") or [],
                "secondary_subjects": row.get("secondary_subjects") or [],
                "subtopic": row.get("subtopic"),
                "concept": row.get("concept"),
                "ask_type": row.get("ask_type"),
                "label_source": row.get("label_source"),
                "question_text": qtext,
                "option_1": row.get("option_1"),
                "option_2": row.get("option_2"),
                "option_3": row.get("option_3"),
                "option_4": row.get("option_4"),
                "answer_key": str(row.get("answer") or "") or None,
                "answer_note": row.get("answer_note"),
                "has_image_ref": has_image_ref(qtext),
            }
        )
    n = 0
    for batch in chunked(payload, 200):
        client.table("questions").upsert(batch, on_conflict="qid").execute()
        n += len(batch)
        print(f"  questions upserted: {n}/{len(payload)}")
    return n


def upsert_topic_stats(client, path: Path) -> int:
    rows = []
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "topic": r["topic"],
                    "primary_subject": r["primary_subject"],
                    "question_count": int(float(r["question_count"])),
                    "years_seen": int(float(r["years_seen"])),
                    "year_list": r.get("year_list"),
                    "recurrence": float(r["recurrence"]) if r.get("recurrence") else None,
                    "recent_count": int(float(r["recent_count"])) if r.get("recent_count") else None,
                    "years_since_last": int(float(r["years_since_last"]))
                    if r.get("years_since_last")
                    else None,
                    "due_for_return": str(r.get("due_for_return", "")).lower() in ("true", "1", "yes"),
                    "importance_score": float(r["importance_score"])
                    if r.get("importance_score")
                    else None,
                    "priority_band": r.get("priority_band"),
                }
            )
    for batch in chunked(rows, 200):
        client.table("topic_stats").upsert(batch, on_conflict="topic,primary_subject").execute()
    print(f"  topic_stats: {len(rows)}")
    return len(rows)


def upsert_overlaps(client, path: Path) -> int:
    client.table("topic_overlaps").delete().neq("id", 0).execute()
    rows = []
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "item_a": r["item_a"],
                    "item_b": r["item_b"],
                    "co_occurrence": int(float(r["co_occurrence"])),
                }
            )
    for batch in chunked(rows, 200):
        client.table("topic_overlaps").upsert(batch, on_conflict="item_a,item_b").execute()
    print(f"  topic_overlaps: {len(rows)}")
    return len(rows)


def upsert_drift(client, path: Path) -> int:
    rows = []
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "topic": r["topic"],
                    "recent_count": float(r["recent_count"]) if r.get("recent_count") else None,
                    "older_count": float(r["older_count"]) if r.get("older_count") else None,
                    "recent_share": float(r["recent_share"]) if r.get("recent_share") else None,
                    "older_share": float(r["older_share"]) if r.get("older_share") else None,
                    "delta_share": float(r["delta_share"]) if r.get("delta_share") else None,
                }
            )
    for batch in chunked(rows, 200):
        client.table("topic_drift").upsert(batch, on_conflict="topic").execute()
    print(f"  topic_drift: {len(rows)}")
    return len(rows)


def upsert_ask_types(client, path: Path) -> int:
    client.table("ask_type_stats").delete().neq("id", 0).execute()
    rows = []
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "subject": r["subject"],
                    "ask_type": r["ask_type"],
                    "count": int(float(r["count"])),
                }
            )
    for batch in chunked(rows, 200):
        client.table("ask_type_stats").upsert(batch, on_conflict="subject,ask_type").execute()
    print(f"  ask_type_stats: {len(rows)}")
    return len(rows)


def upsert_priority(client, path: Path) -> None:
    payload = json.loads(path.read_text())
    client.table("priority_snapshots").upsert(
        {
            "as_of_date": date.today().isoformat(),
            "disclaimer": payload.get("disclaimer"),
            "payload": payload,
        },
        on_conflict="as_of_date",
    ).execute()
    print(f"  priority_snapshots: {date.today().isoformat()}")


def subject_slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def upsert_packs(client, subjects_dir: Path) -> int:
    n = 0
    for path in sorted(subjects_dir.glob("*.md")):
        slug = path.stem
        name = slug.replace("_", " ").title()
        if slug == "obg":
            name = "OBG"
        elif slug == "ent":
            name = "ENT"
        text = path.read_text()
        # Heuristic count from first heading line if present
        m = re.search(r"(\d[\d,]*)\s+questions?", text, re.I)
        qcount = int(m.group(1).replace(",", "")) if m else None
        client.table("subject_packs").upsert(
            {
                "subject_slug": slug,
                "subject_name": name,
                "markdown": text,
                "question_count": qcount,
                "updated_at": date.today().isoformat(),
            },
            on_conflict="subject_slug",
        ).execute()
        n += 1
    print(f"  subject_packs: {n}")
    return n


def sync_web_public(out: Path) -> None:
    """Copy viz + questions into web/ for Next.js (Vercel-safe; no symlinks)."""
    import shutil

    web_root = ROOT / "web"
    if not web_root.exists():
        return

    web_data = web_root / "public" / "data"
    web_data.mkdir(parents=True, exist_ok=True)
    packs = web_data / "packs"
    packs.mkdir(exist_ok=True)
    mapping = [
        ("priorities.json", "priorities.json"),
        ("topic_importance.csv", "topic_importance.csv"),
        ("overlaps.csv", "overlaps.csv"),
        ("drift.csv", "drift.csv"),
        ("ask_type_by_subject.csv", "ask_type_by_subject.csv"),
        ("subject_totals.csv", "subject_totals.csv"),
        ("top_concepts_clean.csv", "top_concepts_clean.csv"),
        ("ask_type_share.csv", "ask_type_share.csv"),
        ("year_subject_matrix.csv", "year_subject_matrix.csv"),
    ]

    for src_name, dest_name in mapping:
        src = out / src_name
        if src.exists():
            shutil.copy2(src, web_data / dest_name)
    for path in (out / "packs").glob("*.md"):
        shutil.copy2(path, packs / path.name)
    print(f"  synced → {web_data}")

    # Real file under web/data (not a symlink into gitignored analysis/web_mirror)
    qsrc = out / "questions.json"
    if qsrc.exists():
        qdest_dir = web_root / "data"
        qdest_dir.mkdir(parents=True, exist_ok=True)
        qdest = qdest_dir / "questions.json"
        if qdest.is_symlink() or qdest.exists():
            qdest.unlink()
        shutil.copy2(qsrc, qdest)
        print(f"  synced questions → {qdest}")


def public_image_paths(row: dict) -> list[str]:
    """Map analysis/data-relative image paths to Next.js public URLs."""
    out = []
    for p in row.get("images") or []:
        p = str(p).lstrip("/")
        if p.startswith("question_images/"):
            out.append(f"/{p}")
        else:
            out.append(f"/question_images/{p}")
    return out


def sync_question_images(web_root: Path) -> int:
    """Copy extracted figures into web/public/question_images for static serving."""
    import shutil

    src = DATA / "question_images"
    dest = web_root / "public" / "question_images"
    if not src.exists():
        return 0
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    n = sum(1 for p in dest.rglob("*") if p.is_file())
    print(f"  synced question images → {dest} ({n} files)")
    return n


def export_local_mirror() -> Path:
    """Write a local JSON mirror for the Next.js app when Supabase is unset."""
    out = ANALYSIS / "data" / "web_mirror"
    out.mkdir(parents=True, exist_ok=True)

    qpath = DATA / "merged_questions.json"
    if qpath.exists():
        rows = json.loads(qpath.read_text())
        slim = []
        for row in rows:
            qtext = row.get("question_text") or ""
            images = public_image_paths(row)
            slim.append(
                {
                    "qid": make_qid(row),
                    "year": row.get("year"),
                    "exam": row.get("exam"),
                    "shift": row.get("shift"),
                    "subject_clean": row.get("subject_clean") or row.get("subject"),
                    "topic_clean": row.get("topic_clean") or row.get("topic"),
                    "topics": row.get("topics") or [],
                    "concept": row.get("concept"),
                    "ask_type": row.get("ask_type"),
                    "question_text": qtext,
                    "option_1": row.get("option_1"),
                    "option_2": row.get("option_2"),
                    "option_3": row.get("option_3"),
                    "option_4": row.get("option_4"),
                    "answer_key": str(row.get("answer") or "") or None,
                    "has_image_ref": has_image_ref(qtext) and not images,
                    "images": images,
                    "image_status": row.get("image_status"),
                }
            )
        (out / "questions.json").write_text(json.dumps(slim))
        print(f"  local mirror questions: {len(slim)} → {out / 'questions.json'}")

    for src, name in [
        (REPORTS / "next_exam_priorities.json", "priorities.json"),
        (PLOTS / "topic_importance.csv", "topic_importance.csv"),
        (PLOTS / "multi_topic_overlaps_top50.csv", "overlaps.csv"),
        (PLOTS / "topic_year_drift.csv", "drift.csv"),
        (PLOTS / "ask_type_by_subject.csv", "ask_type_by_subject.csv"),
    ]:
        if src.exists():
            dest = out / name
            dest.write_bytes(src.read_bytes())
            print(f"  mirrored {src.name}")

    packs_out = out / "packs"
    packs_out.mkdir(exist_ok=True)
    for path in (REPORTS / "subjects").glob("*.md"):
        (packs_out / path.name).write_text(path.read_text())
    print(f"  mirrored packs → {packs_out}")
    sync_web_public(out)
    sync_question_images(ROOT / "web")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-questions", action="store_true")
    parser.add_argument("--local-only", action="store_true", help="Only write web_mirror for offline UI")
    args = parser.parse_args()
    load_dotenv()

    print("Writing local web_mirror…")
    export_local_mirror()

    if args.local_only:
        print("Done (local-only).")
        return

    if not (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") and (
        os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    )):
        print(
            "SUPABASE_* not set — skipped remote seed. "
            "Run with credentials or use --local-only.",
            file=sys.stderr,
        )
        return

    client = get_client()
    print("Seeding Supabase…")
    if not args.skip_questions:
        upsert_questions(client, DATA / "merged_questions.json")
    upsert_topic_stats(client, PLOTS / "topic_importance.csv")
    upsert_overlaps(client, PLOTS / "multi_topic_overlaps_top50.csv")
    upsert_drift(client, PLOTS / "topic_year_drift.csv")
    upsert_ask_types(client, PLOTS / "ask_type_by_subject.csv")
    upsert_priority(client, REPORTS / "next_exam_priorities.json")
    upsert_packs(client, REPORTS / "subjects")
    print("Done.")


if __name__ == "__main__":
    main()
