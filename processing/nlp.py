"""
Light NLP: relevance scoring against keywords, building/amount extraction,
optional LLM-based summarization.
"""
from __future__ import annotations

import re
import os
from typing import List, Tuple, Optional

from config.settings import (
    RELEVANCE_KEYWORDS_EN, RELEVANCE_KEYWORDS_ZH,
    HK_DISTRICTS, TRACKED_BUILDINGS, OPENAI_API_KEY,
)
from utils.helpers import truncate
from utils.logger import logger


def detect_language(text: str) -> str:
    """Cheap CJK detection — avoids langdetect dependency for short strings."""
    if not text:
        return "en"
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return "zh" if cjk > max(5, len(text) * 0.05) else "en"


def relevance_score(title: str, body: str) -> Tuple[float, List[str]]:
    """
    Score 0–1 indicating how likely this article is about HK office floor txns.
    Returns (score, matched_keywords).
    """
    text = f"{title}\n{body or ''}".lower()
    matched: List[str] = []

    for kw in RELEVANCE_KEYWORDS_EN:
        if kw.lower() in text:
            matched.append(kw)
    for kw in RELEVANCE_KEYWORDS_ZH:
        if kw in text:
            matched.append(kw)

    # HK-context boost (must appear or score is heavily penalized)
    hk_terms = ["hong kong", "hk", "香港", "kowloon", "九龍", "central", "中環"]
    hk_hit = any(t in text for t in hk_terms)

    score = min(1.0, len(matched) / 4.0)
    if not hk_hit:
        score *= 0.3
    return score, matched


def extract_buildings(text: str) -> List[str]:
    if not text:
        return []
    found = []
    for b in TRACKED_BUILDINGS:
        if re.search(rf"\b{re.escape(b)}\b", text, re.IGNORECASE):
            found.append(b)
    return list(dict.fromkeys(found))   # preserve order, dedupe


def extract_districts(text: str) -> List[str]:
    if not text:
        return []
    found = []
    for d in HK_DISTRICTS:
        if re.search(rf"\b{re.escape(d)}\b", text, re.IGNORECASE):
            found.append(d)
    return list(dict.fromkeys(found))


_AMOUNT_RE = re.compile(
    r"(?:HK\$|HKD|US\$|USD|\$)\s*([\d,.]+)\s*(billion|bn|million|mn|thousand|[BMK])\b"
    r"|([\d,.]+)\s*(billion|bn|million|mn|thousand)\b",
    re.IGNORECASE,
)


def extract_amounts(text: str) -> List[str]:
    if not text:
        return []
    out = []
    for m in _AMOUNT_RE.finditer(text):
        out.append(m.group(0).strip())
    return out[:10]


def summarize(text: str, max_chars: int = 400) -> str:
    """
    Short summary. Uses OpenAI if key present, else extractive fallback
    (first 2 sentences + key sentence containing $/sqft).
    """
    if not text:
        return ""

    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system",
                     "content": "Summarize this HK office real estate news in 2 sentences. "
                                "Highlight building, floor, area, price/rent, parties if present."},
                    {"role": "user", "content": text[:6000]},
                ],
                max_tokens=180,
                temperature=0.2,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI summarization failed, falling back: {e}")

    # Extractive fallback
    sents = re.split(r"(?<=[.!?。！？])\s+", text.strip())
    if not sents:
        return truncate(text, max_chars)

    picked = sents[:2]
    for s in sents[2:8]:
        if re.search(r"\$|HKD|psf|sq ft|sqft|尺|百萬|億", s, re.IGNORECASE):
            picked.append(s)
            break
    return truncate(" ".join(picked), max_chars)
