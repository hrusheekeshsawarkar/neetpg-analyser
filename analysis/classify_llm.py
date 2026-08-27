#!/usr/bin/env python3
"""
LLM-based subject/topic/concept labeling.

- Replaces fake topic "General" / empty topics
- Supports multi-topic overlap (topics list + primary topic)
- Infers real subtopics (not question text copies)
- Tags ask_type + concept for within-topic analysis
- Concurrent batch workers (--workers) for OpenAI throughput

Usage:
  export LLM_PROVIDER=openai OPENAI_MODEL=gpt-5.6-luna
  python3 analysis/classify_llm.py --workers 8 --batch-size 8
  python3 analysis/classify_llm.py --limit 20   # dry run
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_client import SUBJECTS, available_providers, call_llm, extract_json

DATA = Path("analysis/data/merged_questions.json")
CHECKPOINT = Path("analysis/data/llm_classify_checkpoint.json")

ASK_TYPES = [
    "diagnosis",
    "investigation",
    "drug_of_choice",
    "mechanism",
    "image_identification",
    "management",
    "anatomy_structure",
    "epidemiology",
    "other",
]

# Common LLM spellings → our canonical subject list
SUBJECT_ALIASES = {
    "medicine": "Medicine",
    "general medicine": "Medicine",
    "internal medicine": "Medicine",
    "surgery": "Surgery",
    "general surgery": "Surgery",
    "pediatrics": "Pediatrics",
    "paediatrics": "Pediatrics",
    "obgyn": "OBG",
    "obg": "OBG",
    "obstetrics and gynaecology": "OBG",
    "obstetrics & gynaecology": "OBG",
    "obstetrics and gynecology": "OBG",
    "obstetrics": "OBG",
    "gynecology": "OBG",
    "gynaecology": "OBG",
    "ent": "ENT",
    "orthopedics": "Orthopedics",
    "orthopaedics": "Orthopedics",
    "anesthesia": "Anaesthesia",
    "anaesthesia": "Anaesthesia",
    "anesthesiology": "Anaesthesia",
    "community medicine": "Community Medicine",
    "psm": "Community Medicine",
    "spm": "Community Medicine",
    "forensic": "Forensic Medicine",
    "forensic medicine": "Forensic Medicine",
    "fmt": "Forensic Medicine",
}

SYSTEM_SCHEMA = f"""You classify NEET PG medical exam questions for revision analytics.

Allowed subjects (pick exactly one primary_subject — use these exact spellings):
{', '.join(SUBJECTS)}

Return ONLY valid JSON with this shape:
{{
  "items": [
    {{
      "id": <int>,
      "primary_subject": "<one of allowed subjects>",
      "topics": ["<topic1>", "<topic2>"],
      "primary_topic": "<main topic within primary_subject>",
      "subtopic": "<short specific concept name, NOT the full question>",
      "concept": "<2-8 word clinical concept, e.g. 'ARDS IL-8 role' or 'Wilson disease investigation'>",
      "ask_type": "<one of: {', '.join(ASK_TYPES)}>",
      "secondary_subjects": ["<optional overlapping subjects>"]
    }}
  ]
}}

Rules:
- Never use "General", "Unknown", "Others", or "Mixed" as a topic.
- topics may have 1-3 entries when the question genuinely overlaps (e.g. Biochemistry + Pediatrics).
- primary_topic must be a real syllabus topic (Cardiology, Virology, Fractures, etc.).
- subtopic must be a short label (e.g. "cystine stones", "Nissen fundoplication"), never paste the question.
- If image-based with little text, infer from options + clinical clues.
- Keep every string short. Avoid quotes inside string values; use plain words.
- Return STRICT JSON only. No markdown. No trailing commas.
"""


def needs_label(q: dict, enrich_concepts: bool = False) -> bool:
    t = (q.get("topic_clean") or q.get("topic") or "").strip().lower()
    s = (q.get("subject_clean") or q.get("subject") or "").strip().lower()
    if s in ("", "unknown", "mixed"):
        return True
    if t in ("", "general", "unknown", "others", "mixed"):
        return True
    if enrich_concepts and not q.get("concept"):
        return True
    # subtopic == question text is useless
    sub = (q.get("subtopic") or "").strip()
    qt = (q.get("question_text") or "").strip()
    if sub and qt and sub[:80] == qt[:80] and not q.get("concept"):
        return True
    return False


def normalize_subject(raw: str) -> str:
    s = (raw or "").strip()
    if s in SUBJECTS:
        return s
    low = s.lower()
    if low in SUBJECT_ALIASES:
        return SUBJECT_ALIASES[low]
    for cand in SUBJECTS:
        if cand.lower() == low:
            return cand
    return s


def build_batch_prompt(batch: list[tuple[int, dict]]) -> str:
    lines = [SYSTEM_SCHEMA, "", "Classify these questions:", ""]
    for i, q in batch:
        opts = " | ".join(
            filter(
                None,
                [
                    q.get("option_1"),
                    q.get("option_2"),
                    q.get("option_3"),
                    q.get("option_4"),
                ],
            )
        )
        lines.append(f"ID {i}")
        lines.append(f"  year: {q.get('year')}")
        lines.append(f"  hint_subject: {q.get('subject_clean') or q.get('subject')}")
        lines.append(f"  hint_topic: {q.get('topic_clean') or q.get('topic')}")
        lines.append(f"  question: {(q.get('question_text') or '')[:400]}")
        if opts:
            lines.append(f"  options: {opts[:300]}")
        lines.append("")
    lines.append('Respond with JSON object {{"items":[...]}} covering every ID.')
    return "\n".join(lines)


def apply_labels(qs: list[dict], items: list[dict]) -> int:
    by_id = {int(it["id"]): it for it in items if "id" in it}
    n = 0
    for i, it in by_id.items():
        if i < 0 or i >= len(qs):
            continue
        q = qs[i]
        primary_subject = normalize_subject(it.get("primary_subject") or "")
        topics = [t.strip() for t in (it.get("topics") or []) if t and t.strip()]
        topics = [t for t in topics if t.lower() not in ("general", "unknown", "others", "mixed")]
        primary_topic = (it.get("primary_topic") or (topics[0] if topics else "")).strip()
        if primary_topic.lower() in ("general", "unknown", "others", ""):
            primary_topic = topics[0] if topics else "Unclassified"
        if primary_topic not in topics and primary_topic != "Unclassified":
            topics = [primary_topic] + topics
        subtopic = (it.get("subtopic") or "").strip()
        concept = (it.get("concept") or "").strip()
        ask_type = (it.get("ask_type") or "other").strip()
        secondary = []
        for s in it.get("secondary_subjects") or []:
            ns = normalize_subject(s)
            if ns in SUBJECTS:
                secondary.append(ns)

        if primary_subject in SUBJECTS:
            q["subject_clean"] = primary_subject
            q["subject"] = primary_subject
        q["topic_clean"] = primary_topic
        q["topic"] = primary_topic
        q["topics"] = topics[:3]
        q["subtopic"] = subtopic[:120] if subtopic else concept[:120]
        q["concept"] = concept[:160]
        q["ask_type"] = ask_type if ask_type in ASK_TYPES else "other"
        q["secondary_subjects"] = secondary
        q["label_source"] = "llm"
        n += 1
    return n


def save_json(path: Path, qs: list[dict], lock: threading.Lock) -> None:
    with lock:
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w") as f:
            json.dump(qs, f, indent=2, ensure_ascii=False)
        tmp.replace(path)


def save_progress(qs: list[dict], lock: threading.Lock) -> None:
    """Persist both checkpoint and merged so an abort does not drop labels."""
    save_json(CHECKPOINT, qs, lock)
    save_json(DATA, qs, lock)


def process_batch(
    batch_num: int,
    batch: list[tuple[int, dict]],
    qs: list[dict],
    lock: threading.Lock,
    max_tokens: int,
    retries: int = 3,
) -> tuple[int, str]:
    prompt = build_batch_prompt(batch)
    ids = [i for i, _ in batch]
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            raw = call_llm(prompt, max_tokens=max_tokens, temperature=0.05)
            parsed = extract_json(raw)
            if isinstance(parsed, dict):
                items = parsed.get("items") or parsed.get("results") or []
            else:
                items = parsed
            with lock:
                n = apply_labels(qs, items)
            return n, f"  batch {batch_num}: ids {ids[0]}..{ids[-1]}\n    labeled {n}"
        except Exception as e:
            last_err = e
            time.sleep(min(2 ** attempt, 20))
    return 0, f"  batch {batch_num}: ids {ids[0]}..{ids[-1]}\n    ERROR: {last_err}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--workers", type=int, default=6, help="Concurrent LLM batch workers")
    ap.add_argument("--limit", type=int, default=0, help="Max questions to label (0=all)")
    ap.add_argument("--only-unlabeled", action="store_true", default=True)
    ap.add_argument("--all", action="store_true", help="Relabel everything")
    ap.add_argument(
        "--enrich-concepts",
        action="store_true",
        help="Also label questions that have a topic but lack concept tags",
    )
    ap.add_argument("--sleep", type=float, default=0.05)
    ap.add_argument("--max-tokens", type=int, default=3500)
    args = ap.parse_args()
    if args.all:
        args.only_unlabeled = False

    providers = available_providers()
    print("Providers available:", providers or "NONE")
    if not providers:
        sys.exit(1)

    with open(DATA) as f:
        qs = json.load(f)

    indices = list(range(len(qs)))
    if args.only_unlabeled:
        indices = [
            i for i in indices if needs_label(qs[i], enrich_concepts=args.enrich_concepts)
        ]
    if args.limit:
        indices = indices[: args.limit]

    print(
        f"Total questions: {len(qs)}; to label: {len(indices)}; "
        f"workers={args.workers}; batch_size={args.batch_size}"
    )

    batches: list[tuple[int, list[tuple[int, dict]]]] = []
    for start in range(0, len(indices), args.batch_size):
        batch_idx = indices[start : start + args.batch_size]
        batch = [(i, qs[i]) for i in batch_idx]
        batches.append((start // args.batch_size + 1, batch))

    lock = threading.Lock()
    labeled = 0
    done_batches = 0
    t0 = time.time()
    stopping = threading.Event()

    def _persist(_signum=None, _frame=None):
        print("  saving progress (checkpoint + merged)...", flush=True)
        save_progress(qs, lock)
        if _signum is not None:
            stopping.set()
            print(f"  saved on signal {_signum}; exiting after in-flight batches", flush=True)

    signal.signal(signal.SIGTERM, _persist)
    signal.signal(signal.SIGINT, _persist)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [
            ex.submit(process_batch, num, batch, qs, lock, args.max_tokens)
            for num, batch in batches
        ]
        for fut in as_completed(futs):
            n, msg = fut.result()
            labeled += n
            done_batches += 1
            print(msg, flush=True)
            if args.sleep:
                time.sleep(args.sleep)
            if done_batches % max(1, args.workers) == 0:
                save_progress(qs, lock)
                rate = labeled / max(time.time() - t0, 1)
                print(
                    f"    checkpoint @ {done_batches}/{len(batches)} batches; "
                    f"labeled≈{labeled}; ~{rate:.1f} q/s",
                    flush=True,
                )
            elif done_batches % 2 == 0:
                save_progress(qs, lock)
            if stopping.is_set():
                break

    save_progress(qs, lock)

    remaining = sum(
        1 for q in qs if needs_label(q, enrich_concepts=args.enrich_concepts)
    )
    elapsed = time.time() - t0
    print(
        f"Done in {elapsed/60:.1f} min. Newly labeled this run ≈ {labeled}. "
        f"Still needing work: {remaining}"
    )


if __name__ == "__main__":
    main()
