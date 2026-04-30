"""
Match news articles to transactions on the basis of building name + date proximity.
Returns (transaction_id, confidence) tuples; confidence is rough.
"""
from __future__ import annotations

from datetime import timedelta
from typing import List, Tuple, Optional

from sqlalchemy import and_, or_

from database import session_scope
from database.models import Transaction, NewsArticle
from processing.nlp import extract_buildings


def match_article_to_transactions(
    article: NewsArticle, window_days: int = 30
) -> List[Tuple[int, float]]:
    """
    Returns list of (transaction_id, confidence 0–1).
    A match needs (a) shared building name, and ideally (b) date within window.
    """
    text = f"{article.title}\n{article.raw_text or ''}\n{article.summary or ''}"
    buildings = extract_buildings(text)
    if not buildings:
        return []

    pub_date = article.published_at.date() if article.published_at else None
    matches: List[Tuple[int, float]] = []

    with session_scope() as s:
        for b in buildings:
            q = s.query(Transaction).filter(
                or_(
                    Transaction.building_name_raw.ilike(f"%{b}%"),
                    # also match via Building if linked
                    Transaction.building.has(name=b),
                )
            )
            if pub_date:
                q = q.filter(
                    and_(
                        Transaction.transaction_date >= pub_date - timedelta(days=window_days),
                        Transaction.transaction_date <= pub_date + timedelta(days=window_days * 2),
                    )
                )
            for tx in q.limit(50):
                # Confidence: building match → 0.5; +0.3 within 14d; +0.2 if amount mentioned
                conf = 0.5
                if pub_date and tx.transaction_date:
                    delta = abs((tx.transaction_date - pub_date).days)
                    if delta <= 14:
                        conf += 0.3
                    elif delta <= 30:
                        conf += 0.15
                if tx.price_hkd or tx.rent_hkd_monthly:
                    if "$" in text or "HKD" in text or "billion" in text.lower() or "million" in text.lower():
                        conf += 0.2
                conf = min(1.0, conf)
                matches.append((tx.id, conf))

    # dedupe, keep best per tx
    best: dict[int, float] = {}
    for tx_id, conf in matches:
        best[tx_id] = max(best.get(tx_id, 0.0), conf)
    return [(tx_id, c) for tx_id, c in best.items() if c >= 0.5]
