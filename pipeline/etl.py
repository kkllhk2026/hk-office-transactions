"""
ETL orchestrator: pull from every source, clean & normalize, persist with dedup.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from database import session_scope, init_db
from database.models import (
    Transaction, NewsArticle, IngestionRun, Building,
    news_transaction_link,
)
from ingestion.transactions import ALL_TRANSACTION_SCRAPERS
from ingestion.news import (
    fetch_all_feeds, fetch_full_article, fetch_news_site_links,
    match_article_to_transactions,
)
from processing import (
    parse_floor, normalize_district, normalize_building_name, normalize_grade,
    relevance_score, summarize, detect_language, is_alert,
    extract_buildings, extract_districts, extract_amounts,
)
from utils.logger import logger


# ---------- Transactions ----------
def run_transaction_ingestion() -> Dict[str, int]:
    init_db()
    totals = {"fetched": 0, "inserted": 0, "skipped": 0}

    for ScraperCls in ALL_TRANSACTION_SCRAPERS:
        scraper = ScraperCls()
        run_log = _new_run(scraper.name)
        try:
            records = scraper.fetch_listings()
            totals["fetched"] += len(records)
            inserted = _persist_transactions(records)
            run_log["items_fetched"] = len(records)
            run_log["items_inserted"] = inserted
            run_log["status"] = "success"
            totals["inserted"] += inserted
        except Exception as e:
            logger.exception(f"[{scraper.name}] failed")
            run_log["status"] = "failed"
            run_log["error_message"] = str(e)
        finally:
            _finalize_run(run_log)
    logger.info(f"Transaction totals: {totals}")
    return totals


def _persist_transactions(records: List[Dict[str, Any]]) -> int:
    inserted = 0
    with session_scope() as s:
        for rec in records:
            try:
                # Skip aggregate market stats here; they could go in a separate table
                if rec.get("transaction_type") == "MarketStat":
                    continue

                # Normalize
                rec.setdefault("district", normalize_district(rec.get("district") or rec.get("address_raw")))
                rec["building_name_norm"] = normalize_building_name(rec.get("building_name_raw"))
                rec["grade"] = normalize_grade(rec.get("grade"))

                fi = parse_floor(rec.get("floor_raw"))
                rec["floor_low"] = fi.floor_low
                rec["floor_high"] = fi.floor_high
                rec["floor_zone"] = fi.floor_zone
                rec["is_whole_floor"] = fi.is_whole_floor
                rec["is_partial_floor"] = fi.is_partial_floor
                rec["unit"] = fi.unit

                # Compute psf if missing
                area = rec.get("area_sqft_gross") or rec.get("area_sqft_saleable")
                if area:
                    if rec.get("price_hkd") and not rec.get("price_psf"):
                        rec["price_psf"] = rec["price_hkd"] / area
                    if rec.get("rent_hkd_monthly") and not rec.get("rent_psf_monthly"):
                        rec["rent_psf_monthly"] = rec["rent_hkd_monthly"] / area

                rec["is_alert"] = is_alert(rec)

                # Building upsert — pull tenure model & owner from the
                # curated registry so downstream filters know whether
                # sales on this building are plausible.
                from config.buildings_registry import lookup as lookup_building

                building_id = None
                building_tenure = "unknown"
                if rec.get("building_name_norm"):
                    reg = lookup_building(rec["building_name_norm"]) or {}
                    bld = s.query(Building).filter_by(name=rec["building_name_norm"]).first()
                    if not bld:
                        bld = Building(
                            name=rec["building_name_norm"],
                            address=rec.get("address_raw"),
                            district=reg.get("district") or rec.get("district"),
                            grade=reg.get("grade") or rec.get("grade"),
                            tenure_model=reg.get("tenure_model", "unknown"),
                            owner=reg.get("owner"),
                        )
                        s.add(bld)
                        s.flush()
                    else:
                        # Backfill tenure on existing rows the first time we see them
                        if bld.tenure_model in (None, "unknown") and reg.get("tenure_model"):
                            bld.tenure_model = reg["tenure_model"]
                            bld.owner = bld.owner or reg.get("owner")
                    building_id = bld.id
                    building_tenure = bld.tenure_model or "unknown"

                # Tenure-mismatch flag: a Sale on a single-landlord building
                # is almost always a misclassification by the source. Keep
                # the row but flag it for human review rather than silently
                # dropping data.
                tenure_mismatch = (
                    rec.get("transaction_type") == "Sale"
                    and building_tenure == "single-landlord"
                )
                review_notes = None
                if tenure_mismatch:
                    review_notes = (
                        f"Sale recorded on a single-landlord building "
                        f"({rec.get('building_name_norm')}). Verify against "
                        f"source — likely should be reclassified as Lease."
                    )
                    logger.warning(
                        f"[tenure] Suspect sale on single-landlord building: "
                        f"{rec.get('building_name_norm')} ({rec.get('source')})"
                    )

                # Build Transaction
                tx = Transaction(
                    transaction_date=rec["transaction_date"],
                    building_id=building_id,
                    building_name_raw=rec.get("building_name_raw"),
                    address_raw=rec.get("address_raw"),
                    district=rec.get("district"),
                    floor_raw=rec.get("floor_raw"),
                    floor_low=rec.get("floor_low"),
                    floor_high=rec.get("floor_high"),
                    floor_zone=rec.get("floor_zone"),
                    is_whole_floor=rec.get("is_whole_floor", False),
                    is_partial_floor=rec.get("is_partial_floor", False),
                    unit=rec.get("unit"),
                    area_sqft_gross=rec.get("area_sqft_gross"),
                    area_sqft_saleable=rec.get("area_sqft_saleable"),
                    transaction_type=rec.get("transaction_type", "Sale"),
                    price_hkd=rec.get("price_hkd"),
                    price_psf=rec.get("price_psf"),
                    rent_hkd_monthly=rec.get("rent_hkd_monthly"),
                    rent_psf_monthly=rec.get("rent_psf_monthly"),
                    buyer=rec.get("buyer"),
                    seller=rec.get("seller"),
                    tenant=rec.get("tenant"),
                    landlord=rec.get("landlord"),
                    grade=rec.get("grade"),
                    source=rec.get("source", "unknown"),
                    source_url=rec.get("source_url"),
                    source_record_id=rec.get("source_record_id"),
                    is_alert=rec.get("is_alert", False),
                    tenure_mismatch=tenure_mismatch,
                    review_notes=review_notes,
                    raw_payload=rec.get("raw_payload"),
                )
                s.add(tx)
                try:
                    s.flush()
                    inserted += 1
                except IntegrityError:
                    s.rollback()                # duplicate per uq_tx_dedupe
            except Exception as e:
                logger.warning(f"persist tx failed: {e}")
                s.rollback()
    return inserted


# ---------- News ----------
def run_news_ingestion(hydrate_full_text: bool = True) -> Dict[str, int]:
    init_db()
    run_log = _new_run("news")

    totals = {"fetched": 0, "inserted": 0, "relevant": 0, "matched": 0}
    try:
        # 1. RSS feeds
        rss_entries = fetch_all_feeds()
        # 2. Index pages for non-RSS sources
        index_stubs = fetch_news_site_links()
        all_entries = rss_entries + index_stubs
        totals["fetched"] = len(all_entries)

        for entry in all_entries:
            try:
                inserted, relevant, matched = _persist_article(entry, hydrate_full_text)
                totals["inserted"] += inserted
                totals["relevant"] += relevant
                totals["matched"] += matched
            except Exception as e:
                logger.warning(f"article failed: {entry.get('url')}: {e}")

        run_log["items_fetched"] = totals["fetched"]
        run_log["items_inserted"] = totals["inserted"]
        run_log["status"] = "success"
    except Exception as e:
        logger.exception("news ingestion failed")
        run_log["status"] = "failed"
        run_log["error_message"] = str(e)
    finally:
        _finalize_run(run_log)

    logger.info(f"News totals: {totals}")
    return totals


def _persist_article(entry: Dict[str, Any], hydrate: bool) -> tuple[int, int, int]:
    """Returns (inserted, relevant, matched)."""
    if not entry.get("url") or not entry.get("title"):
        return 0, 0, 0

    with session_scope() as s:
        # dedupe by URL
        existing = s.query(NewsArticle).filter_by(url=entry["url"]).first()
        if existing:
            return 0, 0, 0

        body = entry.get("raw_text") or ""
        if hydrate and len(body) < 400:
            full = fetch_full_article(entry["url"])
            if full:
                body = full

        title = entry["title"]
        score, _ = relevance_score(title, body)
        is_rel = score >= 0.25

        lang = entry.get("language") or detect_language(title + " " + body)
        article = NewsArticle(
            title=title[:500],
            url=entry["url"][:800],
            source=entry.get("source", "unknown"),
            region=entry.get("region", "local"),
            language=lang,
            published_at=entry.get("published_at"),
            raw_text=body[:50000] if body else None,
            summary=summarize(body or title) if is_rel else None,
            summary_lang="en",
            mentioned_buildings=", ".join(extract_buildings(title + " " + body)) or None,
            mentioned_districts=", ".join(extract_districts(title + " " + body)) or None,
            mentioned_amounts=", ".join(extract_amounts(title + " " + body)) or None,
            relevance_score=score,
            is_relevant=is_rel,
        )
        s.add(article)
        s.flush()

        matched = 0
        if is_rel:
            matches = match_article_to_transactions(article)
            for tx_id, conf in matches:
                s.execute(
                    news_transaction_link.insert().values(
                        news_id=article.id,
                        transaction_id=tx_id,
                        confidence=conf,
                    )
                )
                matched += 1

        return 1, (1 if is_rel else 0), matched


# ---------- Run audit log helpers ----------
def _new_run(source: str) -> Dict[str, Any]:
    return {
        "source": source,
        "started_at": datetime.utcnow(),
        "status": "running",
        "items_fetched": 0,
        "items_inserted": 0,
        "items_updated": 0,
        "error_message": None,
    }


def _finalize_run(run_log: Dict[str, Any]) -> None:
    run_log["finished_at"] = datetime.utcnow()
    with session_scope() as s:
        s.add(IngestionRun(**run_log))


# ---------- Entry points ----------
def run_full_pipeline() -> Dict[str, Any]:
    logger.info("=" * 60)
    logger.info("Starting full ETL pipeline")
    tx = run_transaction_ingestion()
    news = run_news_ingestion()
    logger.info(f"Pipeline complete. transactions={tx}, news={news}")
    return {"transactions": tx, "news": news}


if __name__ == "__main__":
    run_full_pipeline()
