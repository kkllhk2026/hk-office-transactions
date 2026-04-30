# Hong Kong Office Floor Transactions Dashboard

An automated, interactive dashboard tracking **office floor sales and leasing
transactions** in Hong Kong — sourced from major commercial agencies, official
data, and a curated set of local & international news outlets. Built with
Python + Streamlit + SQLAlchemy.

> ⚠️ **Read the [Caveats](#caveats) section before deploying.** Several data
> sources have anti-bot protection and Terms of Service that restrict
> automated access. Treat scrapers as best-effort starting points, not
> production-grade integrations.

---

## Features

- **Overview** dashboard with KPIs, district breakdown, and top buildings
- **Unified Feed** combining transactions and news with advanced filters
  (date, district, building, type, floor range, size, price, source region)
- **News page** monitoring local (SCMP, Mingtiandi, HK01, RTHK, The Standard,
  HKBusiness) and foreign (Reuters, FT, Real Estate Asia, Straits Times)
  outlets, with relevance scoring and AI summaries
- **Analytics** with time-series, leasing-vs-sales, floor-band distribution,
  and news/transaction correlation
- **Building Profile** showing all historical floor transactions and linked
  news for any indexed building
- **CSV/Excel upload** as a backup ingestion path (essential for agency
  reports without machine-readable feeds)
- **Alerts** for transactions ≥ HK$100M or ≥ 10,000 sqft (configurable)
- **Daily/hourly automated ETL** via APScheduler or GitHub Actions
- **Robust scraping** with retries, exponential backoff, polite delays, UA
  rotation, and `robots.txt` respect
- **HK-specific normalization** — accurate floor parsing for `15/F`, `8-10/F`,
  `High Zone 35/F`, `G/F`, `B1/F`, Chinese `高層 35/F`, etc.
- **English + Chinese news** supported (auto language detection; optional
  translation hook)

---

## Architecture

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Centaline   │  │ LeasingHub   │  │   Midland    │   …other transaction sources
│   scraper    │  │   scraper    │  │   scraper    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └────────┬────────┴────────┬────────┘
                │                 │
                ▼                 ▼
        ┌────────────────────────────────┐
        │   Processing layer             │
        │   • floor_parser (15/F, 8-10/F)│
        │   • address/building cleaner   │
        │   • alert detector             │
        │   • NLP (relevance, entities)  │
        └────────────────┬───────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │   SQLAlchemy ORM (SQLite/PG)   │
        │   buildings • transactions     │
        │   news_articles • link table   │
        │   ingestion_runs (audit log)   │
        └────────────────┬───────────────┘
                         │
            ┌────────────┴───────────┐
            │                        │
            ▼                        ▼
   ┌────────────────┐       ┌────────────────┐
   │ News pipeline  │       │ Streamlit UI   │
   │ • RSS feeds    │──────▶│ • Overview     │
   │ • Article body │       │ • Feed         │
   │ • Matcher      │       │ • News         │
   │   (news↔txns)  │       │ • Analytics    │
   └────────────────┘       │ • Building     │
                            │ • Settings     │
                            └────────────────┘
```

### Project layout

```
hk-office-dashboard/
├── app.py                           Main Streamlit entrypoint
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── .github/workflows/
│   ├── daily-etl.yml                Scheduled ETL on GitHub-hosted runner
│   └── tests.yml                    Run pytest on every push
├── config/
│   ├── settings.py                  Loads env + constants (keywords, districts)
│   └── sources.yaml                 RSS feeds, scraper URLs, selectors
├── database/
│   ├── models.py                    SQLAlchemy ORM
│   └── db.py                        Engine + session factory
├── ingestion/
│   ├── base_scraper.py              Retries, UA rotation, robots.txt, rate limit
│   ├── transactions/
│   │   ├── centaline.py
│   │   ├── midland.py
│   │   ├── leasinghub.py
│   │   └── rvd_official.py
│   ├── news/
│   │   ├── rss_feeds.py
│   │   ├── scraper_news.py          newspaper3k + BS4 fallback
│   │   └── matcher.py               News ↔ transaction linker
│   └── csv_uploader.py              Manual upload backup
├── processing/
│   ├── floor_parser.py              Parses HK floor notation
│   ├── cleaner.py                   Address/building/district normalizer
│   ├── nlp.py                       Relevance, entities, summaries
│   └── alerts.py                    Big-deal detection
├── pipeline/
│   ├── etl.py                       Orchestrator
│   └── scheduler.py                 APScheduler daemon
├── ui/
│   ├── components.py                Cached loaders + reusable widgets
│   └── pages/
│       ├── overview.py
│       ├── feed.py
│       ├── news.py
│       ├── analytics.py
│       └── building.py
├── utils/
│   ├── logger.py                    loguru with daily rotation
│   └── helpers.py                   Money/area/date parsing
├── tests/
│   ├── test_floor_parser.py         11 cases
│   └── test_cleaner.py              6 cases
├── data/                            SQLite DB lives here
└── logs/                            Daily-rotated logs
```

---

## Setup

### 1. Clone & install

```bash
git clone <your-repo-url> hk-office-dashboard
cd hk-office-dashboard

python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env to set:
#   - DATABASE_URL (SQLite default works fine for <1M rows)
#   - OPENAI_API_KEY (optional, enables better news summaries)
#   - alert thresholds, request delays, etc.
```

### 3. Initialise the database

The DB is auto-created on first run, but you can pre-init:

```bash
python -c "from database import init_db; init_db()"
```

### 4. Run the dashboard

```bash
streamlit run app.py
```

Open <http://localhost:8501>. The first time, the DB is empty — go to
**Settings → Run full ETL**, or upload a CSV.

### 5. Run the ETL pipeline manually

```bash
# Full pipeline (transactions + news)
python -m pipeline.etl

# Or, only the news pass (faster)
python -c "from pipeline.etl import run_news_ingestion; run_news_ingestion()"
```

### 6. Run tests

```bash
pytest tests/ -v
```

---

## Scheduling daily updates

You have **three** options. Pick whichever fits your hosting.

### Option A — GitHub Actions (zero infra)

`.github/workflows/daily-etl.yml` runs the pipeline every day at 22:00 UTC
(06:00 HKT) on a free GitHub-hosted runner and commits the updated SQLite DB
back to the repo. To enable:

1. Push the repo to GitHub.
2. (Optional) Add `OPENAI_API_KEY` in **Settings → Secrets and variables →
   Actions** if you want LLM summaries.
3. Visit the **Actions** tab to trigger a manual run, or wait for the cron.

This is the simplest setup; the dashboard reads from the committed DB.

### Option B — APScheduler daemon (local/VPS)

```bash
# Run forever, daily at 06:00 + hourly news refresh at :15
python -m pipeline.scheduler
```

Use `systemd`, `supervisor`, `pm2`, or a Docker `restart: unless-stopped`
container to keep it alive.

### Option C — System cron

```bash
crontab -e
# Daily at 06:00 HKT — adjust path
0 6 * * * cd /path/to/hk-office-dashboard && /path/to/.venv/bin/python -m pipeline.etl >> logs/cron.log 2>&1
```

---

## Manual data upload

When scrapers are blocked or you have an agency report (CBRE/JLL/Cushman/
Savills/Colliers/Knight Frank quarterly):

1. Open the dashboard → **Settings**
2. Upload a CSV or Excel file with at minimum:
   - `transaction_date` — `2025-11-15` or `15/11/2025`
   - `building_name` — e.g. `Two IFC`
   - `transaction_type` — `Sale` or `Lease`
3. Optional columns (highly recommended): `district`, `address`, `floor`,
   `area_sqft`, `price_hkd`, `rent_hkd_monthly`, `buyer`, `seller`, `tenant`,
   `landlord`, `grade`, `source`, `source_url`

The pipeline normalizes everything (floor parsing, building matching, psf
computation, alert flagging) automatically.

---

## Extending the system

### Add a new news source with RSS

Edit `config/sources.yaml`:

```yaml
rss_feeds:
  - name: "Some HK News Site"
    url: "https://example.com/feed.xml"
    region: "local"          # or "foreign"
    language: "en"           # or "zh"
```

That's it — `fetch_all_feeds()` picks it up automatically.

### Add a new transaction scraper

1. Subclass `BaseScraper` in a new file under `ingestion/transactions/`
2. Implement `fetch_listings()` returning a list of dicts with the keys
   shown in `_persist_transactions()` (see `pipeline/etl.py`)
3. Register the class in `ingestion/transactions/__init__.py`'s
   `ALL_TRANSACTION_SCRAPERS` list

### Add a tracked building

Append to `TRACKED_BUILDINGS` in `config/settings.py`. The cleaner will
match aliases automatically; if you have a known short form (e.g. `2IFC`),
add an alias entry to `_BUILDING_ALIASES` in `processing/cleaner.py`.

### Switch to PostgreSQL

```bash
# In .env
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/hk_office

# requirements.txt — uncomment psycopg2-binary

pip install psycopg2-binary
python -c "from database import init_db; init_db()"
```

The unique-constraint dedup logic and indices port unchanged.

### Use Playwright for JS-heavy sites

Some sites (e.g. Cloudflare-protected ones) require a real browser.
`requirements.txt` has `playwright` commented out — uncomment, then:

```bash
pip install playwright
playwright install chromium
```

In your scraper, instead of `self.get(url)`, fetch via Playwright and pass
the resulting HTML to BeautifulSoup as before.

### Enable Chinese-to-English translation

```bash
pip install deep-translator
```

Then in `.env`:

```
ENABLE_TRANSLATION=true
```

Plug `deep_translator.GoogleTranslator(source='zh-CN', target='en').translate(text)`
into `processing/nlp.py::summarize` for Chinese articles.

---

## Caveats

**Read these before relying on this in production.**

0. **The building registry contains errors.** See
   [VERIFICATION.md](VERIFICATION.md) for what has been independently
   verified, what has not, and what was corrected after initial release.
   Most entries are NOT verified. Do not use the registry for any
   commercial decision without spot-checking the specific buildings you
   care about.

1. **Scraper selectors break.** Centaline, Midland, and LeasingHub HTML
   shape will change without warning. The CSS selectors in
   `config/sources.yaml` are starting points based on typical commercial
   real estate site patterns — verify with your browser's DevTools and
   update before each deployment.

2. **Respect Terms of Service & robots.txt.** Each site has its own ToS.
   The `BaseScraper` honours `robots.txt` by default and uses polite
   delays (1.5–4s), but **you are responsible** for confirming you may
   scrape each source. For commercial reliability, consider licensed
   APIs from Centaline, JLL, CBRE, etc.

3. **Anti-bot protection.** SCMP, Bloomberg, FT, and several agency sites
   use Cloudflare or paywalls. The `requests`-based scraper will fail
   silently on these. Use Playwright (see above), official APIs, or
   accept that you'll only get RSS-level metadata for those sources.

4. **News-to-transaction matching is fuzzy.** The matcher links by
   building name + date proximity (within ±30 days) with a confidence
   ≥ 0.5 threshold. False positives happen when a building is mentioned
   for unrelated reasons (e.g. "the lobby of Two IFC"). Always review
   matches in the Building Profile page before quoting them in reports.

5. **RVD/Land Registry data is aggregate.** The dashboard treats RVD
   stats as `MarketStat` rows, not individual transactions. They're
   stored but not mixed into deal counts. For per-transaction Land
   Registry data, you need licensed access to the Land Registry's
   Property Information Online (IRIS) service.

6. **Floor numbers are best-effort.** The parser handles ~15 common
   notation patterns and Chinese zone keywords. Edge cases (e.g.
   `24/F & 25/F (excluding Unit C)`) may parse imperfectly. The
   `floor_raw` column always preserves the original string so you can
   audit.

7. **Currency assumed HKD.** The pipeline assumes prices/rents are in
   HKD unless explicitly tagged. USD-quoted deals (some international
   investor reports) need pre-cleaning before upload.

8. **Date timezone is naive.** Article timestamps are stored in UTC where
   available, transaction dates are stored as `Date` (no time component).
   The scheduler uses `Asia/Hong_Kong` from `.env`.

9. **No PII or named-individual scraping.** The scrapers only extract
   parties when they're public corporate entities (e.g. "JPMorgan
   Chase", "Sun Hung Kai Properties"). Don't add scraping logic for
   individual buyer/seller names.

---

## Operations runbook

### Daily checks

- **Settings → Diagnostics** — confirm last 5 ingestion runs were
  `success`. A `failed` row pointing to one source is OK; a streak of
  failures across sources usually means an IP block.
- **Logs** — `logs/app_YYYY-MM-DD.log` shows scraper-by-scraper detail.

### When a scraper breaks

1. Open the source URL in your browser → DevTools → Inspector.
2. Find the new selector for transaction rows.
3. Update `config/sources.yaml` → `transaction_sites.<source>.row_selector`.
4. Re-run that single scraper:
   ```python
   from ingestion.transactions.centaline import CentalineScraper
   s = CentalineScraper(); s.fetch_listings(max_pages=1)
   ```
5. If parsing is now wrong, edit `_parse_row()` in the scraper file.

### When you suspect duplicates

The dedup constraint is
`(source, source_record_id, building_name_raw, transaction_date, floor_raw)`.
If a source changes its record IDs, you'll get duplicates. Inspect:

```sql
SELECT source, COUNT(*), COUNT(DISTINCT source_record_id)
FROM transactions GROUP BY source;
```

Reset that source if needed:

```sql
DELETE FROM transactions WHERE source = 'centaline';
```

then re-ingest.

---

## License

MIT (or whatever you prefer — set this for your repo).

## Disclaimer

This tool aggregates publicly available data for analysis purposes. The
authors make no warranty as to the accuracy, completeness, or timeliness of
the data. Do not rely on it as the sole basis for any commercial,
investment, or legal decision. Verify any deal of consequence against the
original source.
