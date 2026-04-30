"""Tests for the tenure-model registry and mismatch detection."""
from datetime import date

from config.buildings_registry import lookup, BUILDING_REGISTRY
from database import init_db, session_scope
from database.models import Transaction, Building
from pipeline.etl import _persist_transactions


def test_registry_has_known_single_landlord_buildings():
    for name in ["Two IFC", "Chater House", "Cheung Kong Center",
                 "Pacific Place", "International Commerce Centre"]:
        meta = lookup(name)
        assert meta is not None, f"{name} should be in registry"
        assert meta["tenure_model"] == "single-landlord"


def test_registry_has_known_strata_buildings():
    for name in ["The Center", "Lippo Centre", "Cosco Tower",
                 "World-Wide House"]:
        meta = lookup(name)
        assert meta is not None, f"{name} should be in registry"
        assert meta["tenure_model"] == "strata"


def test_registry_lookup_case_insensitive():
    assert lookup("two ifc") is not None
    assert lookup("TWO IFC") is not None
    assert lookup(None) is None
    assert lookup("") is None
    assert lookup("Some Random Building") is None


def test_sale_on_single_landlord_is_flagged():
    init_db()

    # Use a unique source so this test is independent
    sample = [{
        "source": "test_tenure_mismatch",
        "transaction_date": date(2025, 11, 15),
        "building_name_raw": "Two IFC",
        "address_raw": "8 Finance Street, Central",
        "floor_raw": "35/F",
        "area_sqft_gross": 12000,
        "transaction_type": "Sale",       # ← suspect: shouldn't happen at Two IFC
        "price_hkd": 480_000_000,
    }]
    _persist_transactions(sample)

    with session_scope() as s:
        tx = (s.query(Transaction)
                .filter_by(source="test_tenure_mismatch")
                .order_by(Transaction.id.desc()).first())
        assert tx is not None
        assert tx.tenure_mismatch is True
        assert "single-landlord" in (tx.review_notes or "").lower()

        # Building should be tagged correctly
        bld = s.query(Building).filter_by(name="Two IFC").first()
        assert bld.tenure_model == "single-landlord"


def test_lease_on_single_landlord_is_not_flagged():
    init_db()
    sample = [{
        "source": "test_tenure_ok",
        "transaction_date": date(2025, 11, 16),
        "building_name_raw": "Two IFC",
        "floor_raw": "35/F",
        "area_sqft_gross": 12000,
        "transaction_type": "Lease",      # ← legitimate
        "rent_hkd_monthly": 1_500_000,
    }]
    _persist_transactions(sample)

    with session_scope() as s:
        tx = (s.query(Transaction)
                .filter_by(source="test_tenure_ok")
                .order_by(Transaction.id.desc()).first())
        assert tx is not None
        assert tx.tenure_mismatch is False
        assert tx.review_notes is None


def test_sale_on_strata_is_not_flagged():
    init_db()
    sample = [{
        "source": "test_strata_ok",
        "transaction_date": date(2025, 11, 17),
        "building_name_raw": "The Center",
        "floor_raw": "30/F",
        "area_sqft_gross": 22000,
        "transaction_type": "Sale",       # ← legitimate at strata building
        "price_hkd": 1_300_000_000,
    }]
    _persist_transactions(sample)

    with session_scope() as s:
        tx = (s.query(Transaction)
                .filter_by(source="test_strata_ok")
                .order_by(Transaction.id.desc()).first())
        assert tx is not None
        assert tx.tenure_mismatch is False
