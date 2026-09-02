#!/usr/bin/env python3
"""Shared helpers for sync scripts (qid, image detection)."""

from __future__ import annotations

import hashlib
import re

IMAGE_RE = re.compile(
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
    return bool(IMAGE_RE.search(text or ""))
