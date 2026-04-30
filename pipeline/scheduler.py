"""
Standalone scheduler daemon. Run with:
    python -m pipeline.scheduler
"""
from __future__ import annotations

import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import RUN_DAILY_AT, TIMEZONE
from pipeline.etl import run_full_pipeline, run_news_ingestion
from utils.logger import logger


def _job_full() -> None:
    logger.info(f"[scheduler] daily full pipeline at {datetime.now()}")
    try:
        run_full_pipeline()
    except Exception as e:
        logger.exception(f"[scheduler] full pipeline failed: {e}")


def _job_news() -> None:
    logger.info(f"[scheduler] hourly news refresh at {datetime.now()}")
    try:
        run_news_ingestion(hydrate_full_text=False)   # cheap pass
    except Exception as e:
        logger.exception(f"[scheduler] news refresh failed: {e}")


def main() -> None:
    sched = BlockingScheduler(timezone=TIMEZONE)

    hour, minute = (int(x) for x in RUN_DAILY_AT.split(":"))
    sched.add_job(_job_full, CronTrigger(hour=hour, minute=minute), id="daily_full")
    sched.add_job(_job_news, CronTrigger(minute=15), id="hourly_news")  # at :15

    def _shutdown(*_):
        logger.info("[scheduler] shutting down")
        sched.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info(f"[scheduler] started. daily={RUN_DAILY_AT} {TIMEZONE}, hourly news at :15")
    sched.start()


if __name__ == "__main__":
    main()
