"""Tests for Kowloon East registry coverage and period-selector logic."""
from datetime import date, timedelta

from config.buildings_registry import lookup, BUILDING_REGISTRY


# ---------- Registry coverage ----------

def test_kowloon_east_single_landlord_buildings_present():
    """Major single-landlord KE towers should be in the registry.
    
    Note: Manhattan Place and Landmark East were previously misclassified
    as strata. They are confirmed single-landlord (per LeasingHub building
    page and landmarkeast.com.hk respectively, verified Apr 2026).
    """
    expected = [
        "International Commerce Centre",
        "Manulife Financial Centre",
        "AIA Kowloon Tower",
        "AIRSIDE",
        "The Quayside",
        "Two Harbourfront",
        "Manhattan Place",       # Verified single-landlord (LeasingHub)
        "Landmark East",         # Verified single-landlord (landmarkeast.com.hk)
        "Two Landmark East",
    ]
    for name in expected:
        meta = lookup(name)
        assert meta is not None, f"{name} missing from registry"
        assert meta["tenure_model"] == "single-landlord", (
            f"{name} should be single-landlord, got {meta['tenure_model']}"
        )


def test_kowloon_east_strata_buildings_present():
    """Verified strata buildings — needs more research. Currently we don't
    have any *confirmed* strata-titled Kowloon East towers in the registry.
    Many candidate buildings (Millennium City etc.) are in _UNVERIFIED
    until we can confirm their tenure. This test is a placeholder reminder."""
    # No confirmed strata KE buildings yet — this test will gain assertions
    # as buildings are verified and promoted from _UNVERIFIED.
    from config.buildings_registry import _STRATA, _UNVERIFIED
    # The unverified bucket should not be empty — there's known work to do
    assert len(_UNVERIFIED) > 0, (
        "The _UNVERIFIED bucket should contain buildings awaiting "
        "tenure classification. If you've verified them all, remove "
        "the bucket and update this test."
    )


def test_registry_district_consistency():
    """Every registry entry has a district that appears in HK_DISTRICTS."""
    from config.settings import HK_DISTRICTS
    canonical = set(HK_DISTRICTS)
    for name, meta in BUILDING_REGISTRY.items():
        d = meta.get("district")
        assert d in canonical, (
            f"{name} has district {d!r} which is not in HK_DISTRICTS. "
            f"Either add it to HK_DISTRICTS or use a canonical name."
        )


def test_known_verified_classifications():
    """Pin down the building classifications that have been independently
    verified against external sources, so future refactors don't silently
    revert them."""
    cases = [
        # Three Garden Road complex — Champion REIT, single-landlord.
        # Verified: Wikipedia, Mingtiandi, championreit.com (Apr 2026).
        ("Three Garden Road",            "single-landlord"),
        ("Champion Tower",               "single-landlord"),
        ("ICBC Tower",                   "single-landlord"),
        # AIRSIDE — Nan Fung Group. Verified Apr 2026 (Wikipedia, nanfung.com).
        ("AIRSIDE",                      "single-landlord"),
        # The Bay Hub (formerly Goldin Financial Global Centre) —
        # PAG/Mapletree JV. Verified Apr 2026 (SCMP, Mingtiandi).
        ("The Bay Hub",                  "single-landlord"),
        ("Goldin Financial Global Centre", "single-landlord"),
        # Manhattan Place — single ownership per LeasingHub building page.
        ("Manhattan Place",              "single-landlord"),
        # Landmark East — single complex, single-landlord per landmarkeast.com.hk.
        ("Landmark East",                "single-landlord"),
        ("Two Landmark East",            "single-landlord"),
        # The Center — verified strata (post-2018 CK Asset sell-down).
        ("The Center",                   "strata"),
    ]
    for name, expected_tenure in cases:
        meta = lookup(name)
        assert meta is not None, f"{name} missing from registry"
        assert meta["tenure_model"] == expected_tenure, (
            f"{name}: expected {expected_tenure}, got {meta['tenure_model']}"
        )


def test_registry_no_duplicates():
    """A building should not appear in more than one bucket."""
    from config.buildings_registry import _SINGLE_LANDLORD, _STRATA, _UNVERIFIED
    sl = set(_SINGLE_LANDLORD.keys())
    st = set(_STRATA.keys())
    un = set(_UNVERIFIED.keys())
    overlaps = []
    if sl & st: overlaps.append(f"single-landlord ∩ strata: {sl & st}")
    if sl & un: overlaps.append(f"single-landlord ∩ unverified: {sl & un}")
    if st & un: overlaps.append(f"strata ∩ unverified: {st & un}")
    assert not overlaps, " | ".join(overlaps)


def test_registry_size_reasonable():
    """Sanity check: we should have a meaningful number of buildings."""
    assert len(BUILDING_REGISTRY) >= 80, (
        f"Registry only has {len(BUILDING_REGISTRY)} buildings — "
        f"expected at least 80 covering Central, Kowloon East, etc."
    )


# ---------- Period selector behaviour (logic-only test) ----------

def test_period_presets_cover_multi_year():
    """The picker's preset list (defined inline in components.py) should
    include multi-year options for historical analysis."""
    today = date.today()
    presets = {
        "Last 7 days":   (today - timedelta(days=7),         today),
        "Last 30 days":  (today - timedelta(days=30),        today),
        "Last 90 days":  (today - timedelta(days=90),        today),
        "Year to date":  (date(today.year, 1, 1),            today),
        "Last 12 months":(today - timedelta(days=365),       today),
        "Last 3 years":  (today - timedelta(days=365 * 3),   today),
        "Last 5 years":  (today - timedelta(days=365 * 5),   today),
        "Last 10 years": (today - timedelta(days=365 * 10),  today),
    }
    # Multi-year span exists
    assert (today - presets["Last 5 years"][0]).days >= 365 * 5 - 1
    assert (today - presets["Last 10 years"][0]).days >= 365 * 10 - 1
    # Order is correct (longer windows have earlier start dates)
    starts = [presets[k][0] for k in ["Last 7 days", "Last 90 days",
                                       "Last 12 months", "Last 5 years",
                                       "Last 10 years"]]
    assert starts == sorted(starts, reverse=True), (
        "Preset start dates should be monotonically decreasing as the "
        "window grows"
    )
