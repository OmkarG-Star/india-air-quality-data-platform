"""Local lake layout: raw JSON and bronze Parquet, partitioned by date.

Writes are idempotent: re-running a day overwrites that day's partition,
so backfills and retries never create duplicates.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

DEFAULT_DATA_DIR = Path("data")


def raw_path(data_dir: Path, day: date, city_slug: str, source: str = "open_meteo") -> Path:
    return data_dir / "raw" / f"source={source}" / f"date={day.isoformat()}" / f"{city_slug}.json"


def bronze_path(data_dir: Path, day: date) -> Path:
    return data_dir / "bronze" / "air_quality_hourly" / f"date={day.isoformat()}" / "part-000.parquet"


def write_raw(data_dir: Path, day: date, city_slug: str, payload: dict) -> Path:
    path = raw_path(data_dir, day, city_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)  # atomic swap: readers never see a half-written file
    return path


def write_bronze(data_dir: Path, day: date, frame: pd.DataFrame) -> Path:
    path = bronze_path(data_dir, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    frame.to_parquet(tmp, index=False)
    tmp.replace(path)
    return path
