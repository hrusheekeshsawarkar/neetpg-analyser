#!/usr/bin/env python3
"""Sanity-check OpenRouter free text + OCR models (does not touch Gemini classify job)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm_client import (  # noqa: E402
    OPENROUTER_OCR_MODELS,
    available_providers,
    call_llm,
    call_llm_vision,
    extract_json,
)


def main():
    print("Providers:", available_providers())
    if "openrouter" not in available_providers():
        print("Set OPENROUTER_API_KEY in .env first")
        return 1

    print("\n1) Text JSON smoke (OpenRouter preferred via LLM_PROVIDER)...")
    import os

    os.environ["LLM_PROVIDER"] = "openrouter"
    # reload preference
    from llm_client import available_providers as ap

    print("  order:", ap())
    raw = call_llm(
        'Return ONLY JSON: {"ok": true, "provider": "openrouter"}',
        max_tokens=80,
    )
    print("  raw:", raw[:200])
    print("  parsed:", extract_json(raw))

    print("\n2) OCR candidates:", OPENROUTER_OCR_MODELS)
    # Tiny 1x1 PNG — proves image payload accepted (not real OCR)
    # Real OCR: render a PDF page with pdf2image/pdfplumber and pass bytes.
    png_1x1 = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
        b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    print("\n3) Vision payload smoke (tiny PNG)...")
    try:
        v = call_llm_vision(
            "Reply with JSON only: {\"saw_image\": true}",
            png_1x1,
            mime="image/png",
            max_tokens=80,
        )
        print("  raw:", v[:250])
        print("  parsed:", extract_json(v))
    except Exception as e:
        print("  vision smoke failed (rate limit / model):", e)

    print("\nDone. For PDF OCR: render page → call_llm_vision(prompt, page_png_bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
