# Data Verification Status

This document tracks which parts of the building registry and demo data
have been independently verified, and which are flagged as needing review.

**Last updated: 30 April 2026**

## ⚠ Important honest disclosure

The original registry I shipped contained known errors. A user spot-checked
it and identified that single-landlord vs. strata classifications were
incorrect for several buildings. After targeted verification:

- ✅ **Some entries are now verified** against current public sources
- ⚠ **Most entries are NOT independently verified** — they reflect general
  market knowledge that may be stale or wrong
- ❌ **Some original entries were factually wrong** and have been corrected
  (see "Corrections made" below)

**Do not use this registry for any commercial decision without verifying
the specific buildings you care about.** It's a starting point, not a
ground truth.

---

## ✅ Verified (with sources)

| Building | Tenure | Owner | Source / date |
|---|---|---|---|
| Three Garden Road (formerly Citibank Plaza) | single-landlord | Champion REIT | Wikipedia, Mingtiandi, championreit.com — Apr 2026 |
| Champion Tower | single-landlord | Champion REIT | Same as above (renamed from Citibank Tower 2016) |
| ICBC Tower | single-landlord | Champion REIT | Same as above |
| AIRSIDE | single-landlord | Nan Fung Group | Wikipedia, nanfung.com — Apr 2026 |
| The Bay Hub (formerly Goldin Financial Global Centre) | single-landlord | PAG / Mapletree JV | SCMP March 2024, Mingtiandi May 2023 |
| Manhattan Place | single-landlord | Single owner | LeasingHub building page (2022) |
| Landmark East | single-landlord | Single owner | landmarkeast.com.hk |
| Two Landmark East | single-landlord | Single owner | Same complex as Landmark East |
| The Millennity | single-landlord | SHKP / Transport International | shkp.com press release |
| The Center | strata | Multiple post-2018 | Widely reported CK Asset strata sell-down 2018 |

## ⚠ Unverified (in registry but not independently checked)

Most of the registry. Specifically these need verification before relying:

- **Hongkong Land Central portfolio** (Chater House, Exchange Square, Jardine
  House, Alexandra House, Gloucester Tower, Edinburgh Tower) — believed
  single-landlord but not verified against current Hongkong Land disclosures
- **Swire Properties portfolio** (Pacific Place, Three Pacific Place, One
  Island East, Taikoo Place complex, Cityplaza) — believed single-landlord
- **Hysan Lee Garden series** — believed single-landlord
- **All HK Island strata** (Lippo Centre, Cosco Tower, Hopewell Centre,
  Wing On Centre, etc.) — needs current verification, especially as some
  may have changed status
- **Most Kowloon East entries** — moved to `_UNVERIFIED` bucket pending
  research

## ❌ Corrections made (April 2026)

These entries were wrong in earlier versions and have been fixed:

1. **`Citibank Plaza`** — Removed as separate entry. The complex was renamed
   to "Three Garden Road" in 2016. Both towers (Champion Tower and ICBC
   Tower) are owned by Champion REIT, which acquired remaining floors in 2013.
   Previous entry "Citibank Plaza: Champion REIT (single landlord)" was kept
   but is now an alias.

2. **`Manhattan Place`** — Was classified as **strata** (Multiple owners).
   This was wrong; LeasingHub explicitly lists it as a "single ownership
   Commercial Building." Reclassified as single-landlord.

3. **`Landmark East`** and **`Two Landmark East`** — Were classified as
   strata. Both towers are operated as a single dedicated complex
   (landmarkeast.com.hk) with unified leasing. Reclassified as single-
   landlord.

4. **`Goldin Financial Global Centre`** — Owner listed as "Goldin / mainland
   investor consortium." Goldin defaulted; the building was sold to a
   PAG/Mapletree joint venture in 2023 for HK$5.6B and renamed
   "The Bay Hub" in 2024.

5. **`Enterprise Square Five (MegaBox)`** — This was a fabricated name
   that conflated two separate buildings. Removed.

6. **`Millennium City`** (single entry, "mixed phases") — Previously listed
   as a single strata entry. Replaced with individual MC1/MC2/MC3/MC5/MC6
   entries, all moved to `_UNVERIFIED` because I'm not confident about their
   actual tenure (likely SHKP single-landlord but needs confirmation).

7. **Demo data** — The 1,100 random transactions in the HTML preview were
   generated with `Math.random()`. Despite the realistic-looking numbers,
   no transaction in the demo is a real HK deal. This is now stated more
   prominently in the preview banner.

## How to verify a building yourself

1. **Centaline OIR** (`oir.centanet.com`) — search for the building. The
   property page often states "Single owner" / "Multiple owners" explicitly.
2. **LeasingHub** (`leasinghub.com`) — building pages note ownership type.
3. **HKEX filings** — for buildings owned by listed REITs (Champion, Link,
   Sunlight, Fortune), the latest annual report lists the portfolio with
   current ownership %.
4. **Hong Kong Land Registry** — paid service, but definitive for any
   specific floor/unit.
5. **Direct from owner's website** — Hongkong Land, Swire Properties,
   Sun Hung Kai, Hysan all publish their HK office portfolios.

## Process recommendation

Before deploying this dashboard for any real use:

1. Have a HK commercial real estate professional review the registry
2. Run the dashboard with real data and look at the tenure-mismatch flags —
   each flag is either a real source-side error or a registry error; both
   need investigation
3. Set a quarterly reminder to re-verify the top 30 buildings (those
   driving the most transaction volume in your data)
4. Consider switching to a paid commercial database (CoStar, REIS, agency
   licensed feeds) for the underlying ownership data
