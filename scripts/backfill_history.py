"""
Backfill historical transaction data from one or more CSV/Excel files.

Use cases:
  • Initial load — populate years of history from agency archives or a
    Centaline/Midland export
  • Recovery — re-import after a database wipe
  • Bulk upload of multiple files (e.g. one CSV per year)

Usage:
    python -m scripts.backfill_history /path/to/file1.csv /path/to/file2.xlsx
    python -m scripts.backfill_history data/history/*.csv

Each file must contain at minimum:
    transaction_date, building_name, transaction_type
And optionally:
    district, address, floor, area_sqft, price_hkd, rent_hkd_monthly,
    buyer, seller, tenant, landlord, grade, source, source_url

After loading, run:
    python -c "from pipeline.etl import run_news_ingestion; run_news_ingestion()"
to pull news articles and link them to the historical transactions.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

from database import init_db
from ingestion.csv_uploader import parse_upload
from pipeline.etl import _persist_transactions
from utils.logger import logger


def backfill(paths: List[str]) -> dict:
    init_db()
    totals = {"files": 0, "rows_parsed": 0, "rows_inserted": 0, "errors": []}

    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            msg = f"File not found: {path}"
            logger.error(msg)
            totals["errors"].append(msg)
            continue

        logger.info(f"Loading {path.name}…")
        try:
            with open(path, "rb") as f:
                data = f.read()
            records = parse_upload(data, path.name)
            inserted = _persist_transactions(records)
            totals["files"] += 1
            totals["rows_parsed"] += len(records)
            totals["rows_inserted"] += inserted
            logger.info(
                f"  {path.name}: parsed {len(records)} rows, "
                f"inserted {inserted} new ({len(records) - inserted} duplicates skipped)"
            )
        except Exception as e:
            msg = f"{path.name}: {e}"
            logger.exception(msg)
            totals["errors"].append(msg)

    return totals


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    paths = sys.argv[1:]
    # Expand globs that the shell didn't expand (Windows-friendly)
    expanded = []
    for p in paths:
        if "*" in p or "?" in p:
            from glob import glob
            expanded.extend(glob(p))
        else:
            expanded.append(p)

    if not expanded:
        print("No files matched.")
        sys.exit(1)

    totals = backfill(expanded)
    print("\n" + "=" * 60)
    print(f"Files processed:  {totals['files']}")
    print(f"Rows parsed:      {totals['rows_parsed']:,}")
    print(f"Rows inserted:    {totals['rows_inserted']:,}")
    print(f"Duplicates:       {totals['rows_parsed'] - totals['rows_inserted']:,}")
    if totals["errors"]:
        print(f"Errors ({len(totals['errors'])}):")
        for e in totals["errors"]:
            print(f"  • {e}")
    print("=" * 60)


if __name__ == "__main__":
    main()
