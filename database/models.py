"""SQLAlchemy ORM models for transactions, news, buildings, and links."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Text, DateTime, Date, Boolean,
    ForeignKey, UniqueConstraint, Index, Table
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# Many-to-many link: a news article can mention multiple transactions
news_transaction_link = Table(
    "news_transaction_link",
    Base.metadata,
    Column("news_id", Integer, ForeignKey("news_articles.id"), primary_key=True),
    Column("transaction_id", Integer, ForeignKey("transactions.id"), primary_key=True),
    Column("confidence", Float, default=0.0),
    Column("matched_at", DateTime, default=datetime.utcnow),
)


class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    name_zh = Column(String(255))
    address = Column(String(500))
    district = Column(String(120), index=True)
    sub_district = Column(String(120))
    grade = Column(String(8))             # A / B / C
    completion_year = Column(Integer)
    total_floors = Column(Integer)
    latitude = Column(Float)
    longitude = Column(Float)

    # Tenure model: how the building is actually transacted in HK practice.
    #   'single-landlord' — owned by one party (e.g. Hongkong Land, Swire,
    #     IFC Development); only LEASING happens. A sale record on this
    #     building is almost always a misclassification.
    #   'strata'          — strata-titled, multiple owners; both sales and
    #     leases are normal (e.g. The Center, Lippo Centre, Cosco Tower).
    #   'mixed'           — predominantly single-landlord but with some
    #     strata floors (rare).
    #   'unknown'         — default until classified.
    tenure_model = Column(String(20), default="unknown", index=True)
    owner = Column(String(255))

    notes = Column(Text)

    transactions = relationship("Transaction", back_populates="building")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    transaction_date = Column(Date, nullable=False, index=True)

    building_id = Column(Integer, ForeignKey("buildings.id"))
    building_name_raw = Column(String(255))      # what the source said
    address_raw = Column(String(500))
    district = Column(String(120), index=True)

    # Floor info — both raw + parsed
    floor_raw = Column(String(120))              # "8-10/F", "High Zone 35/F"
    floor_low = Column(Integer)                  # 8
    floor_high = Column(Integer)                 # 10
    floor_zone = Column(String(40))              # Low / Mid / High / None
    is_whole_floor = Column(Boolean, default=False)
    is_partial_floor = Column(Boolean, default=False)
    unit = Column(String(80))                    # Unit A, etc.

    area_sqft_gross = Column(Float)
    area_sqft_saleable = Column(Float)

    transaction_type = Column(String(20), nullable=False, index=True)  # Sale / Lease

    # Money
    price_hkd = Column(Float)                    # for sales
    price_psf = Column(Float)                    # HKD / sqft
    rent_hkd_monthly = Column(Float)             # for leases
    rent_psf_monthly = Column(Float)

    # Parties (often undisclosed)
    buyer = Column(String(255))
    seller = Column(String(255))
    tenant = Column(String(255))
    landlord = Column(String(255))

    grade = Column(String(8))                    # A / B / C if known
    source = Column(String(80), nullable=False)  # centaline / midland / ...
    source_url = Column(String(500))
    source_record_id = Column(String(120))       # native id from source if any

    is_alert = Column(Boolean, default=False, index=True)

    # True if a Sale record landed on a single-landlord building (probable
    # misclassification by the source); the row is kept but flagged for review.
    tenure_mismatch = Column(Boolean, default=False, index=True)
    review_notes = Column(String(500))

    raw_payload = Column(Text)                   # original JSON/HTML snippet

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    building = relationship("Building", back_populates="transactions")
    news_articles = relationship(
        "NewsArticle", secondary=news_transaction_link, back_populates="transactions"
    )

    __table_args__ = (
        UniqueConstraint(
            "source", "source_record_id",
            "building_name_raw", "transaction_date", "floor_raw",
            name="uq_tx_dedupe",
        ),
        Index("idx_tx_district_date", "district", "transaction_date"),
        Index("idx_tx_type_date", "transaction_type", "transaction_date"),
        Index("idx_tx_building_date", "building_id", "transaction_date"),
        Index("idx_tx_tenure_mismatch", "tenure_mismatch"),
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(String(800), nullable=False, unique=True)
    source = Column(String(120), nullable=False, index=True)
    region = Column(String(20))                  # local / foreign
    language = Column(String(8))                 # en / zh / ...
    published_at = Column(DateTime, index=True)

    raw_text = Column(Text)
    summary = Column(Text)
    summary_lang = Column(String(8))

    # Extracted entities
    mentioned_buildings = Column(Text)           # comma-separated
    mentioned_districts = Column(Text)
    mentioned_amounts = Column(Text)             # JSON list of {value, unit}

    sentiment = Column(String(20))               # positive / neutral / negative
    relevance_score = Column(Float, default=0.0)
    is_relevant = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship(
        "Transaction", secondary=news_transaction_link, back_populates="news_articles"
    )

    __table_args__ = (
        Index("idx_news_pub_relevant", "published_at", "is_relevant"),
    )


class IngestionRun(Base):
    """Audit log of every pipeline run."""
    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    source = Column(String(120))
    status = Column(String(40))                  # success / partial / failed
    items_fetched = Column(Integer, default=0)
    items_inserted = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    error_message = Column(Text)
