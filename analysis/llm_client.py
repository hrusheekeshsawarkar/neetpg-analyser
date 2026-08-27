#!/usr/bin/env python3
"""Shared LLM client: Gemini → OpenRouter → OpenAI → BHT (first available key wins)."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Union

# Free OpenRouter OCR / multimodal candidates (IDs verified Aug 2026)
NEMOTRON_ULTRA = "nvidia/nemotron-3-ultra-550b-a55b:free"
NEMOTRON_NANO_OMNI = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

OPENROUTER_OCR_MODELS = [
    NEMOTRON_NANO_OMNI,  # works; good JSON
    "google/gemma-4-26b-a4b-it:free",  # often 429 on free tier
    "google/gemma-4-31b-it:free",
    "dots-studio/dots-3-note-preview:free",  # doc/note OCR-ish
]

# Text/JSON labeling fallbacks (used when OpenAI/Gemini fail)
OPENROUTER_TEXT_MODELS = [
    NEMOTRON_ULTRA,  # free 550B; stream to collect content + reasoning
    NEMOTRON_NANO_OMNI,
    "google/gemma-4-26b-a4b-it:free",
]


def _load_dotenv():
    """Load analysis/.env or repo .env if present (never commit these files)."""
    roots = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for env_path in roots:
        if not env_path.is_file():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


_load_dotenv()


SUBJECTS = [
    "Anatomy",
    "Biochemistry",
    "Physiology",
    "Pharmacology",
    "Microbiology",
    "Pathology",
    "Community Medicine",
    "Forensic Medicine",
    "Ophthalmology",
    "ENT",
    "Medicine",
    "Surgery",
    "OBG",
    "Pediatrics",
    "Anaesthesia",
    "Orthopedics",
    "Radiology",
    "Psychiatry",
    "Dermatology",
]


def _env(*names: str) -> Optional[str]:
    for n in names:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    return None


def available_providers() -> list[str]:
    """Providers with keys set. If LLM_PROVIDER is set, use only that provider."""
    preferred = (_env("LLM_PROVIDER") or "").lower().strip()
    out = []
    if _env("OPENAI_API_KEY"):
        out.append("openai")
    if _env("OPENROUTER_API_KEY"):
        out.append("openrouter")
    if _env("BHT_LLM_KEY"):
        out.append("bht")
    if preferred:
        if preferred not in out:
            return []
        return [preferred]
    return out


def call_llm(prompt: str, max_tokens: int = 4000, temperature: float = 0.1) -> str:
    """Call the configured provider (see LLM_PROVIDER)."""
    providers = available_providers()
    if not providers:
        raise RuntimeError(
            "No LLM API key found (or LLM_PROVIDER points to a missing key). "
            "Set OPENAI_API_KEY, OPENROUTER_API_KEY, or BHT_LLM_KEY."
        )

    errors = []
    for p in providers:
        try:
            if p == "openrouter":
                return _call_openrouter(
                    prompt, max_tokens=max_tokens, temperature=temperature
                )
            if p == "openai":
                return _call_openai(prompt, max_tokens=max_tokens, temperature=temperature)
            if p == "bht":
                return _call_bht(prompt, max_tokens=max_tokens, temperature=temperature)
        except Exception as e:
            errors.append(f"{p}: {e}")
            continue
    raise RuntimeError("All LLM providers failed: " + "; ".join(errors))


def call_llm_vision(
    prompt: str,
    image_bytes: bytes,
    mime: str = "image/png",
    max_tokens: int = 4000,
    temperature: float = 0.1,
) -> str:
    """OCR / vision call via OpenRouter free multimodal models (Gemini fallback if set)."""
    errors = []
    if _env("OPENROUTER_API_KEY"):
        try:
            return _call_openrouter(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                image_bytes=image_bytes,
                mime=mime,
                prefer_ocr=True,
            )
        except Exception as e:
            errors.append(f"openrouter: {e}")
    # Text-only Gemini cannot take images here; skip unless we add native vision later
    raise RuntimeError(
        "Vision/OCR failed. Set OPENROUTER_API_KEY and use a free multimodal model. "
        + "; ".join(errors)
    )

def _call_gemini(prompt: str, max_tokens: int, temperature: float) -> str:
    key = _env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    # Prefer flash for cost/speed; fall back handled by caller retries if needed
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    # Try preferred model, then common fallbacks (API model names change often)
    candidates = [model, "gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-pro"]
    seen = set()
    last_err = None
    for m in candidates:
        if m in seen:
            continue
        seen.add(m)
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{m}:generateContent?key={key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read())
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Gemini failed for models {list(seen)}: {last_err}")


def _call_openrouter(
    prompt: str,
    max_tokens: int,
    temperature: float,
    image_bytes: Optional[bytes] = None,
    mime: str = "image/png",
    prefer_ocr: bool = False,
) -> str:
    key = _env("OPENROUTER_API_KEY")
    default = os.environ.get("OPENROUTER_MODEL", NEMOTRON_ULTRA)
    # Note: short alias nvidia/nemotron-3-nano-omni:free does NOT exist — use full id
    pool = (
        OPENROUTER_OCR_MODELS
        if (prefer_ocr or image_bytes is not None)
        else OPENROUTER_TEXT_MODELS
    )
    candidates = [default] + [m for m in pool if m != default]

    content: list | str
    if image_bytes is not None:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            },
        ]
    else:
        content = prompt

    seen = set()
    last_err = None
    for model in candidates:
        if model in seen:
            continue
        seen.add(model)
        use_stream = _openrouter_should_stream(model)
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
            "stream": use_stream,
        }
        # Some reasoning models reject custom temperature
        if not use_stream:
            payload["temperature"] = temperature
        try:
            if use_stream:
                content_out = _openrouter_stream(key, payload)
            else:
                content_out = _openrouter_once(key, payload)
            if not content_out:
                last_err = f"{model}: empty content"
                continue
            return content_out
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            last_err = f"{model} HTTP {e.code}: {body}"
            if e.code in (429, 403, 404, 502, 503):
                continue
            raise
        except Exception as e:
            last_err = f"{model}: {e}"
            continue
    raise RuntimeError(f"OpenRouter failed: {last_err}")


def _openrouter_should_stream(model: str) -> bool:
    m = model.lower()
    return "ultra" in m or "reasoning" in m


def _openrouter_headers(key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://github.com/neetpg-analyser",
        "X-Title": "neetpg-analyser",
    }


def _openrouter_message_text(msg: dict) -> str:
    content_out = msg.get("content")
    if isinstance(content_out, list):
        content_out = "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in content_out
        )
    if not content_out:
        content_out = msg.get("reasoning") or ""
    return (content_out or "").strip()


def _openrouter_once(key: str, payload: dict) -> str:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers=_openrouter_headers(key),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"empty choices {str(data)[:200]}")
    return _openrouter_message_text(choices[0].get("message") or {})


def _openrouter_stream(key: str, payload: dict) -> str:
    """SSE stream — needed for some reasoning models to surface content (and usage)."""
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers=_openrouter_headers(key),
        method="POST",
    )
    chunks: list[str] = []
    with urllib.request.urlopen(req, timeout=180) as resp:
        while True:
            line = resp.readline()
            if not line:
                break
            line = line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            delta = ((obj.get("choices") or [{}])[0].get("delta") or {})
            piece = delta.get("content") or ""
            if isinstance(piece, list):
                piece = "".join(
                    p.get("text", "") if isinstance(p, dict) else str(p) for p in piece
                )
            if piece:
                chunks.append(piece)
            msg = ((obj.get("choices") or [{}])[0].get("message") or {})
            if msg.get("content") and not chunks:
                chunks.append(_openrouter_message_text(msg))
    return "".join(chunks).strip()


def _openai_model_quirks(model: str) -> dict:
    """GPT-5 / o-series often reject custom temperature and use max_completion_tokens."""
    m = model.lower()
    return {
        "fixed_temperature": m.startswith(("gpt-5", "o1", "o3", "o4")),
        "max_completion_tokens": m.startswith(("gpt-5", "o1", "o3", "o4")),
    }


def _call_openai(prompt: str, max_tokens: int, temperature: float) -> str:
    key = _env("OPENAI_API_KEY")
    # Best cost/quality for high-volume medical JSON labeling (verified Aug 2026):
    # gpt-5.6-luna ≈ $0.20/$1.20 per 1M tokens — prefer over legacy gpt-4o-mini.
    model = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")
    quirks = _openai_model_quirks(model)
    payload: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }
    if quirks["max_completion_tokens"]:
        # Leave headroom: some gpt-5 models spend completion budget on reasoning.
        payload["max_completion_tokens"] = max(max_tokens, 1200)
    else:
        payload["max_tokens"] = max_tokens
        payload["temperature"] = temperature
    # fixed_temperature models only accept default (omit the field)

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    if not content:
        raise RuntimeError(
            f"OpenAI {model} returned empty content (usage={data.get('usage')})"
        )
    return content


def _call_bht(prompt: str, max_tokens: int, temperature: float) -> str:
    key = _env("BHT_LLM_KEY")
    model = os.environ.get("BHT_MODEL", "bht/large")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        "https://llmapi-key.ris.bht-berlin.de/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-api-key": key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def extract_json(text: str):
    """Parse JSON from model output (array or object, possibly fenced / with think tags)."""
    if not text:
        raise ValueError("empty LLM response")
    s = text.strip()
    # Strip common reasoning wrappers
    for tag in ("</think>", "</thinking>"):
        if tag in s:
            s = s.split(tag)[-1].strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].strip()

    candidates = []
    if "[" in s:
        start, end = s.find("["), s.rfind("]")
        if start >= 0 and end > start:
            candidates.append(s[start : end + 1])
    if "{" in s:
        start, end = s.find("{"), s.rfind("}")
        if start >= 0 and end > start:
            candidates.append(s[start : end + 1])
    candidates.append(s)

    last_err = None
    for cand in candidates:
        for variant in (cand, _repair_json_text(cand)):
            try:
                return json.loads(variant)
            except Exception as e:
                last_err = e
                continue
    # Last resort: pull individual {...} objects that look like items
    items = _extract_item_objects(s)
    if items:
        return {"items": items}
    raise ValueError(f"Could not parse JSON: {last_err}")


def _repair_json_text(s: str) -> str:
    """Best-effort fixes for common LLM JSON issues."""
    import re

    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    # trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    # Python-ish literals
    s = re.sub(r"\bNone\b", "null", s)
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)
    return s


def _extract_item_objects(s: str) -> list:
    """Extract dicts containing an 'id' field when full JSON is broken."""
    import re

    objs = []
    for m in re.finditer(r"\{[^{}]*\"id\"\s*:\s*\d+[^{}]*\}", s, re.S):
        chunk = _repair_json_text(m.group(0))
        try:
            objs.append(json.loads(chunk))
        except Exception:
            continue
    return objs
