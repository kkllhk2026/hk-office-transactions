"""
Curated registry of HK office building tenure models.

╔══════════════════════════════════════════════════════════════════════════╗
║  ⚠ DATA QUALITY WARNING — READ BEFORE TRUSTING THIS FILE ⚠              ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  This registry was hand-curated from publicly available sources and      ║
║  market knowledge. It contains errors. Specifically, it is known that:   ║
║                                                                          ║
║   • Ownership data may be outdated. HK office buildings change hands     ║
║     (REIT acquisitions, en-bloc sales, strata partitions). Verified      ║
║     entries below note the source date; everything else needs            ║
║     independent verification before use in any commercial context.       ║
║                                                                          ║
║   • Tenure classification is best-effort. A building marked              ║
║     'single-landlord' may have had a strata partition we don't know      ║
║     about, or vice versa. The classification drives the tenure-          ║
║     mismatch flag — getting it wrong causes false alarms or missed       ║
║     misclassifications.                                                  ║
║                                                                          ║
║   • Building names and grades may not match what data sources use.       ║
║     'Three Garden Road' is the official name for what was 'Citibank      ║
║     Plaza' (renamed 2016). Match logic should be tolerant of aliases.    ║
║                                                                          ║
║  Before relying on this in production:                                   ║
║    1. Spot-check 10-20 buildings against current public sources          ║
║       (Centaline OIR, agency websites, HKEX filings)                     ║
║    2. Have a HK commercial real estate professional review the list      ║
║    3. Set up a process to update the registry quarterly                  ║
║    4. Always treat tenure-mismatch flags as 'review' signals, not        ║
║       'reject' signals — manual verification is required                 ║
║                                                                          ║
║  Sources verified (date of verification noted inline):                   ║
║    • Three Garden Road / Citibank Plaza — Champion REIT (Wikipedia,      ║
║      Mingtiandi, championreit.com — consistent across sources)           ║
║    • AIRSIDE — Nan Fung Group (Wikipedia, nanfung.com)                   ║
║    • Goldin Financial Global Centre — sold to PAG/Mapletree JV in 2023,  ║
║      now branded "The Bay Hub" (SCMP, Mingtiandi)                        ║
║    • Manhattan Place — single ownership, not strata (LeasingHub)         ║
║    • Landmark East — single ownership, not strata (landmarkeast.com.hk)  ║
║                                                                          ║
║  Many other entries in this file are NOT independently verified.         ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

A "tenure model" determines how a building is transacted in real-world HK
practice. It's NOT the same thing as the building grade.

  • single-landlord — held entirely by one entity that leases out floors.
                      Sale records on these buildings are almost always a
                      data-entry mistake by the source. The pipeline keeps
                      them but flags `tenure_mismatch=True` for review.

  • strata          — strata-titled, multiple owners; both sales and leases
                      occur normally at floor level.

  • mixed           — predominantly single-landlord but with a small number
                      of strata-titled floors (rare; treat sales with
                      caution and verify manually).

  • unknown         — default until a human classifies it.
"""
from __future__ import annotations

from typing import Dict, TypedDict


class BuildingMeta(TypedDict, total=False):
    district: str
    grade: str
    tenure_model: str
    owner: str


# ---- Single-landlord prime towers ----
# These are the "sales should not happen here" buildings. Verified against
# common HK market knowledge as of mid-2020s; verify before relying on for
# legal or commercial decisions.

_SINGLE_LANDLORD: Dict[str, BuildingMeta] = {
    # IFC complex
    "Two IFC":                         {"owner": "IFC Development (SHK / Henderson / MTR)", "district": "Central",       "grade": "A"},
    "One IFC":                         {"owner": "IFC Development (SHK / Henderson / MTR)", "district": "Central",       "grade": "A"},

    # Hongkong Land Central portfolio
    "Chater House":                    {"owner": "Hongkong Land",                            "district": "Central",       "grade": "A"},
    "Exchange Square":                 {"owner": "Hongkong Land",                            "district": "Central",       "grade": "A"},
    "Jardine House":                   {"owner": "Hongkong Land",                            "district": "Central",       "grade": "A"},
    "Alexandra House":                 {"owner": "Hongkong Land",                            "district": "Central",       "grade": "A"},
    "Gloucester Tower":                {"owner": "Hongkong Land",                            "district": "Central",       "grade": "A"},
    "Edinburgh Tower":                 {"owner": "Hongkong Land",                            "district": "Central",       "grade": "A"},
    "One & Two Exchange Square":       {"owner": "Hongkong Land",                            "district": "Central",       "grade": "A"},

    # CK Asset
    "Cheung Kong Center":              {"owner": "CK Asset Holdings",                        "district": "Central",       "grade": "A"},
    "Cheung Kong Center II":           {"owner": "CK Asset Holdings",                        "district": "Central",       "grade": "A"},

    # Owner-occupier / dedicated-owner Central towers
    "AIA Central":                     {"owner": "AIA Group",                                "district": "Central",       "grade": "A"},
    "Bank of China Tower":             {"owner": "Bank of China",                            "district": "Central",       "grade": "A"},
    "HSBC Main Building":              {"owner": "HSBC Holdings",                            "district": "Central",       "grade": "A"},

    # Three Garden Road complex (formerly Citibank Plaza, renamed 2016).
    # Champion REIT acquired remaining floors in 2013 → 100% single-landlord.
    # Includes Champion Tower (formerly Citibank Tower, 47F) and ICBC Tower (37F).
    # Verified: Wikipedia, Mingtiandi, championreit.com (2025).
    "Three Garden Road":               {"owner": "Champion REIT",                            "district": "Central",       "grade": "A"},
    "Champion Tower":                  {"owner": "Champion REIT",                            "district": "Central",       "grade": "A"},
    "ICBC Tower":                      {"owner": "Champion REIT",                            "district": "Central",       "grade": "A"},

    "The Henderson":                   {"owner": "Henderson Land",                           "district": "Central",       "grade": "A"},

    # Swire Properties — Pacific Place + Island East
    "Pacific Place":                   {"owner": "Swire Properties",                         "district": "Admiralty",     "grade": "A"},
    "One Pacific Place":               {"owner": "Swire Properties",                         "district": "Admiralty",     "grade": "A"},
    "Two Pacific Place":               {"owner": "Swire Properties",                         "district": "Admiralty",     "grade": "A"},
    "Three Pacific Place":             {"owner": "Swire Properties",                         "district": "Wan Chai",      "grade": "A"},
    "One Island East":                 {"owner": "Swire Properties",                         "district": "Quarry Bay",    "grade": "A"},
    "Two Taikoo Place":                {"owner": "Swire Properties",                         "district": "Taikoo",        "grade": "A"},
    "Taikoo Place":                    {"owner": "Swire Properties",                         "district": "Taikoo",        "grade": "A"},
    "Cambridge House":                 {"owner": "Swire Properties",                         "district": "Taikoo",        "grade": "A"},
    "Devon House":                     {"owner": "Swire Properties",                         "district": "Taikoo",        "grade": "A"},
    "Dorset House":                    {"owner": "Swire Properties",                         "district": "Taikoo",        "grade": "A"},
    "Lincoln House":                   {"owner": "Swire Properties",                         "district": "Taikoo",        "grade": "A"},
    "Oxford House":                    {"owner": "Swire Properties",                         "district": "Taikoo",        "grade": "A"},
    "PCCW Tower":                      {"owner": "Swire Properties / PCCW",                  "district": "Taikoo",        "grade": "A"},

    # Hysan / Lee Garden
    "Hysan Place":                     {"owner": "Hysan Development",                        "district": "Causeway Bay",  "grade": "A"},
    "Lee Garden One":                  {"owner": "Hysan Development",                        "district": "Causeway Bay",  "grade": "A"},
    "Lee Garden Two":                  {"owner": "Hysan Development",                        "district": "Causeway Bay",  "grade": "A"},
    "Lee Garden Three":                {"owner": "Hysan Development",                        "district": "Causeway Bay",  "grade": "A"},
    "Lee Garden Six":                  {"owner": "Hysan Development",                        "district": "Causeway Bay",  "grade": "A"},
    "Lee Theatre Plaza":               {"owner": "Hysan Development",                        "district": "Causeway Bay",  "grade": "A"},

    # Wharf
    "Times Square":                    {"owner": "Wharf Holdings",                           "district": "Causeway Bay",  "grade": "A"},
    "Harbour City":                    {"owner": "Wharf Holdings",                           "district": "Tsim Sha Tsui", "grade": "A"},
    "Wheelock House":                  {"owner": "Wharf Holdings",                           "district": "Central",       "grade": "A"},

    # Other prime single-landlord towers
    "K11 Atelier":                     {"owner": "New World Development",                    "district": "Tsim Sha Tsui", "grade": "A"},
    "K11 Atelier King's Road":         {"owner": "New World Development",                    "district": "Quarry Bay",    "grade": "A"},
    "Cityplaza":                       {"owner": "Swire Properties",                         "district": "Taikoo",        "grade": "A"},

    # ---- Kowloon East — single-landlord ----
    # Kowloon East is HK's secondary CBD, covering Kwun Tong, Kowloon Bay,
    # and the Kai Tak development zone. It has a HIGHER mix of strata
    # buildings than HK Island, but several major Grade A towers are
    # held by single landlords.
    "International Commerce Centre":   {"owner": "Sun Hung Kai / MTR",                       "district": "Kowloon East",  "grade": "A"},   # West Kowloon, often grouped with KE in market reports
    "Manulife Financial Centre":       {"owner": "Manulife",                                 "district": "Kwun Tong",     "grade": "A"},
    "Two Harbourfront":                {"owner": "Wharf Holdings",                           "district": "Hung Hom",      "grade": "A"},
    "AIA Kowloon Tower":               {"owner": "AIA Group / Nan Fung",                     "district": "Kowloon Bay",   "grade": "A"},
    # Goldin Financial Global Centre — sold to PAG/Mapletree JV 2023 for
    # HK$5.6B, rebranded "The Bay Hub" 2024. Still single-landlord.
    # Verified: SCMP March 2024, Mingtiandi May 2023.
    "The Bay Hub":                     {"owner": "PAG / Mapletree JV",                       "district": "Kowloon Bay",   "grade": "A"},
    "Goldin Financial Global Centre":  {"owner": "PAG / Mapletree JV (renamed The Bay Hub)",  "district": "Kowloon Bay",   "grade": "A"},
    "MegaBox":                         {"owner": "Kerry Properties",                         "district": "Kowloon Bay",   "grade": "B"},
    # ---- Kowloon East — single-landlord (additions verified separately) ----
    # Manhattan Place — single ownership per LeasingHub building page (2022).
    # Verified: leasinghub.com/building/manhattan-place
    "Manhattan Place":                 {"owner": "Single owner (per LeasingHub listing)",    "district": "Kowloon Bay",   "grade": "A"},
    # Landmark East — operated under single dedicated brand (landmarkeast.com.hk),
    # both towers leased as a single property. Likely single-landlord.
    # Verified: landmarkeast.com.hk
    "Landmark East":                   {"owner": "Single owner (Landmark East complex)",     "district": "Kwun Tong",     "grade": "A"},
    "Two Landmark East":               {"owner": "Single owner (Landmark East complex)",     "district": "Kwun Tong",     "grade": "A"},
    # The Millennity (formerly part of Millennium City master plan) —
    # SHKP & Transport International JV; single-landlord lease asset.
    # Verified: shkp.com press release.
    "The Millennity":                  {"owner": "SHKP / Transport International",           "district": "Kwun Tong",     "grade": "A"},

    # AIRSIDE — Nan Fung Group flagship. 47-storey, opened 2023.
    # Verified: Wikipedia, Nan Fung Group, CBRE.
    "AIRSIDE":                         {"owner": "Nan Fung Group",                           "district": "Kai Tak",       "grade": "A"},

    # The following are believed to be single-landlord but not independently
    # verified. Check before relying on these:
    "The Quayside":                    {"owner": "Link REIT / Nan Fung (unverified)",        "district": "Kwun Tong",     "grade": "A"},
    "Kerry Centre":                    {"owner": "Kerry Properties (unverified)",            "district": "Quarry Bay",    "grade": "A"},
    "Enterprise Square Three":         {"owner": "Sun Hung Kai Properties (unverified)",     "district": "Kowloon Bay",   "grade": "A"},
    "Skyline Tower":                   {"owner": "Sun Hung Kai Properties (unverified)",     "district": "Kowloon Bay",   "grade": "A"},
    "One Kowloon":                     {"owner": "Sun Hung Kai Properties (unverified)",     "district": "Kowloon Bay",   "grade": "A"},
    "Billion Centre":                  {"owner": "Sun Hung Kai Properties (unverified)",     "district": "Kowloon Bay",   "grade": "B"},

    "International Trade Tower":       {"owner": "Goodman Group (unverified)",               "district": "Cheung Sha Wan","grade": "A"},
}


# ---- Strata-title towers ----
# These are the buildings where individual floor sales legitimately occur.
# Note: Kowloon East historically has the HIGHEST share of strata-titled
# Grade A/B towers in HK — it's where most of the floor-level sale market
# actually happens. Many of these were built post-2010 by SHK/Henderson/
# CK Asset and sold floor-by-floor to end-users and investors.
_STRATA: Dict[str, BuildingMeta] = {
    # ---- Hong Kong Island ----
    "The Center":                      {"owner": "Multiple (post-2018 strata)", "district": "Central",      "grade": "A"},
    "World-Wide House":                {"owner": "Multiple",                    "district": "Central",      "grade": "B"},
    "Wing On Centre":                  {"owner": "Multiple",                    "district": "Sheung Wan",   "grade": "B"},
    "Cosco Tower":                     {"owner": "Multiple",                    "district": "Sheung Wan",   "grade": "A"},
    "Lippo Centre":                    {"owner": "Multiple",                    "district": "Admiralty",    "grade": "A"},
    "Hopewell Centre":                 {"owner": "Multiple",                    "district": "Wan Chai",     "grade": "B"},
    "China Resources Building":        {"owner": "Multiple",                    "district": "Wan Chai",     "grade": "A"},
    "Manulife Plaza":                  {"owner": "Multiple",                    "district": "Causeway Bay", "grade": "B"},
    "Two Chinachem Plaza":             {"owner": "Multiple",                    "district": "Central",      "grade": "B"},
    "Tower 535":                       {"owner": "Multiple",                    "district": "Causeway Bay", "grade": "B"},
}


# ---- UNVERIFIED — needs human review ----
# These buildings are tagged as 'unknown' tenure. The pipeline will NOT
# flag tenure mismatches on them. Promote to _SINGLE_LANDLORD or _STRATA
# only after verifying against current public sources.
_UNVERIFIED: Dict[str, BuildingMeta] = {
    "Millennium City 1":               {"owner": "Unverified",                  "district": "Kwun Tong",    "grade": "A"},
    "Millennium City 2":               {"owner": "Unverified",                  "district": "Kwun Tong",    "grade": "A"},
    "Millennium City 3":               {"owner": "Unverified",                  "district": "Kwun Tong",    "grade": "A"},
    "Millennium City 5":               {"owner": "Unverified",                  "district": "Kwun Tong",    "grade": "A"},
    "Millennium City 6":               {"owner": "Unverified",                  "district": "Kwun Tong",    "grade": "A"},
    "Two Harbour Square":              {"owner": "Unverified",                  "district": "Kwun Tong",    "grade": "A"},
    "EGL Tower":                       {"owner": "Unverified",                  "district": "Kwun Tong",    "grade": "B"},
    "Eastern Centre":                  {"owner": "Unverified",                  "district": "Kwun Tong",    "grade": "B"},
    "Kowloon Commerce Centre":         {"owner": "Unverified",                  "district": "Kwai Chung",   "grade": "A"},
    "Mapletree Bay Point":             {"owner": "Mapletree (verify whether strata-let)", "district": "Kwun Tong", "grade": "A"},
}


# ---- Final lookup ----
def _build_registry() -> Dict[str, BuildingMeta]:
    out: Dict[str, BuildingMeta] = {}
    for name, meta in _SINGLE_LANDLORD.items():
        out[name] = {**meta, "tenure_model": "single-landlord"}
    for name, meta in _STRATA.items():
        out[name] = {**meta, "tenure_model": "strata"}
    for name, meta in _UNVERIFIED.items():
        out[name] = {**meta, "tenure_model": "unknown"}
    return out
    return out


BUILDING_REGISTRY: Dict[str, BuildingMeta] = _build_registry()


def lookup(building_name: str | None) -> BuildingMeta | None:
    """Case-insensitive exact lookup against the registry."""
    if not building_name:
        return None
    target = building_name.strip().lower()
    for name, meta in BUILDING_REGISTRY.items():
        if name.lower() == target:
            return meta
    return None
