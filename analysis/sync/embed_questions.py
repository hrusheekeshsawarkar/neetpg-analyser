#!/usr/bin/env python3
"""
Embed questions into Supabase pgvector.

Requires:
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
  OPENAI_API_KEY

Usage:
  python analysis/sync/embed_questions.py
  python analysis/sync/embed_questions.py --all
  python analysis/sync/embed_questions.py --limit 100
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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


def get_supabase():
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


def embed_text(client_oa, text: str, model: str) -> list[float]:
    resp = client_oa.embeddings.create(model=model, input=text[:8000])
    return resp.data[0].embedding


def build_embed_text(row: dict) -> str:
    parts = [
        f"Subject: {row.get('subject_clean') or ''}",
        f"Topic: {row.get('topic_clean') or ''}",
        f"Concept: {row.get('concept') or ''}",
        f"Ask type: {row.get('ask_type') or ''}",
        f"Question: {row.get('question_text') or ''}",
        "Options: "
        + " ".join(
            [
                f"A) {row.get('option_1') or ''}",
                f"B) {row.get('option_2') or ''}",
                f"C) {row.get('option_3') or ''}",
                f"D) {row.get('option_4') or ''}",
            ]
        ),
    ]
    return "\n".join(parts)


def fetch_rows(sb, need_all: bool, limit: int | None) -> list[dict]:
    cols = (
        "qid,subject_clean,topic_clean,concept,ask_type,"
        "question_text,option_1,option_2,option_3,option_4,embedding"
    )
    # Paginate
    page_size = 1000
    offset = 0
    out: list[dict] = []
    while True:
        q = sb.table("questions").select(cols).range(offset, offset + page_size - 1)
        if not need_all:
            q = q.is_("embedding", "null")
        res = q.execute()
        batch = res.data or []
        if not batch:
            break
        out.extend(batch)
        offset += page_size
        if limit and len(out) >= limit:
            out = out[:limit]
            break
        if len(batch) < page_size:
            break
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Re-embed all rows")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default=os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small"))
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    load_dotenv()

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY required for embeddings")

    from openai import OpenAI

    oa = OpenAI()
    sb = get_supabase()
    rows = fetch_rows(sb, need_all=args.all, limit=args.limit)
    print(f"Embedding {len(rows)} questions with {args.model}…")

    done = 0
    for i in range(0, len(rows), args.batch_size):
        batch = rows[i : i + args.batch_size]
        texts = [build_embed_text(r) for r in batch]
        # OpenAI batch embeddings
        resp = oa.embeddings.create(model=args.model, input=[t[:8000] for t in texts])
        vectors = [d.embedding for d in resp.data]
        for row, vec in zip(batch, vectors):
            sb.table("questions").update({"embedding": vec}).eq("qid", row["qid"]).execute()
            done += 1
        print(f"  {done}/{len(rows)}")
        time.sleep(0.2)

    # Coverage report
    total = sb.table("questions").select("qid", count="exact").execute()
    missing = (
        sb.table("questions")
        .select("qid", count="exact")
        .is_("embedding", "null")
        .execute()
    )
    t = total.count or 0
    m = missing.count or 0
    covered = t - m
    pct = (100.0 * covered / t) if t else 0.0
    print(f"Coverage: {covered}/{t} ({pct:.1f}%) embedded; missing={m}")


if __name__ == "__main__":
    main()
