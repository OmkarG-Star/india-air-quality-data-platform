"""Daily ingestion job: API -> raw JSON -> bronze Parquet.

Usage:
    python -m aqp.ingest                      # yesterday (IST)
    python -m aqp.ingest --date 2026-09-29
    python -m aqp.ingest --start 2026-09-01 --end 2026-09-07   # backfill
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from aqp.client import AirQualityClient
from aqp.config import DEFAULT_CONFIG, PipelineConfig, load_config
from aqp.storage import DEFAULT_DATA_DIR, write_bronze, write_raw
from aqp.transform import check_quality, to_bronze

logger = logging.getLogger("aqp.ingest")


def run_day(
    day: date,
    config: PipelineConfig,
    client: AirQualityClient,
    data_dir: Path = DEFAULT_DATA_DIR,
    strict: bool = False,
) -> bool:
    """Ingest every city for one day. Returns True if the day loaded cleanly."""
    ingested_at = datetime.now(ZoneInfo(config.timezone))
    frames, failed = [], []

    for city in config.cities:
        try:
            payload = client.fetch_day(city, day, config.hourly_variables, config.timezone)
        except Exception as exc:  # one city failing must not block the others
            logger.error("Failed to fetch %s for %s: %s", city.name, day, exc)
            failed.append(city.name)
            continue
        write_raw(data_dir, day, city.slug, payload)
        frames.append(to_bronze(payload, city, ingested_at))

    if not frames:
        logger.error("No data loaded for %s", day)
        return False

    bronze = pd.concat(frames, ignore_index=True)
    report = check_quality(bronze)
    for issue in report.issues:
        logger.warning("Quality check (%s): %s", day, issue)

    if strict and not report.passed:
        logger.error("Strict mode: not writing bronze for %s", day)
        return False

    path = write_bronze(data_dir, day, bronze)
    logger.info("Wrote %d rows for %s to %s", len(bronze), day, path)
    return not failed and report.passed


def _date_range(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("--end must be on or after --start")
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest hourly air-quality data for Indian cities.")
    parser.add_argument("--date", type=date.fromisoformat, help="Day (YYYY-MM-DD). Default: yesterday.")
    parser.add_argument("--start", type=date.fromisoformat, help="Backfill start (YYYY-MM-DD).")
    parser.add_argument("--end", type=date.fromisoformat, help="Backfill end (YYYY-MM-DD).")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--strict", action="store_true", help="Fail the day if any quality check fails.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    args = parse_args(argv)
    config = load_config(args.config)

    if args.start or args.end:
        if not (args.start and args.end):
            raise SystemExit("--start and --end must be used together")
        days = _date_range(args.start, args.end)
    else:
        today = datetime.now(ZoneInfo(config.timezone)).date()
        days = [args.date or today - timedelta(days=1)]

    client = AirQualityClient()
    results = [run_day(day, config, client, args.data_dir, args.strict) for day in days]
    logger.info("Finished: %d/%d days loaded cleanly", sum(results), len(results))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
