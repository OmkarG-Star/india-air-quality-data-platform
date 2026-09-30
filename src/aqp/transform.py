"""Flatten raw API responses into a tidy bronze table and run basic quality checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from aqp.config import City

# API variable name -> bronze column name
COLUMN_MAP = {
    "pm10": "pm10",
    "pm2_5": "pm2_5",
    "carbon_monoxide": "co",
    "nitrogen_dioxide": "no2",
    "sulphur_dioxide": "so2",
    "ozone": "o3",
    "us_aqi": "us_aqi",
    "european_aqi": "european_aqi",
}

POLLUTANT_COLUMNS = ["pm10", "pm2_5", "co", "no2", "so2", "o3"]
KEY_COLUMNS = ["city", "observed_at"]


def to_bronze(payload: dict, city: City, ingested_at: datetime, source: str = "open_meteo") -> pd.DataFrame:
    """One row per city per hour. Missing variables become nulls, never silent drops."""
    hourly = payload["hourly"]
    frame = pd.DataFrame({"observed_at": pd.to_datetime(hourly["time"])})

    for api_name, column in COLUMN_MAP.items():
        values = hourly.get(api_name)
        frame[column] = pd.to_numeric(pd.Series(values), errors="coerce") if values is not None else pd.NA

    frame.insert(0, "city", city.name)
    frame.insert(1, "state", city.state)
    frame.insert(2, "latitude", city.latitude)
    frame.insert(3, "longitude", city.longitude)
    frame["source"] = source
    frame["ingested_at"] = pd.Timestamp(ingested_at)
    return frame


@dataclass
class QualityReport:
    rows: int
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.issues


def check_quality(frame: pd.DataFrame, expected_hours: int = 24) -> QualityReport:
    """Lightweight checks now; these become dbt tests in week 3."""
    report = QualityReport(rows=len(frame))

    if frame.empty:
        report.issues.append("no rows")
        return report

    duplicates = frame.duplicated(subset=KEY_COLUMNS).sum()
    if duplicates:
        report.issues.append(f"{duplicates} duplicate (city, observed_at) rows")

    for city, count in frame.groupby("city").size().items():
        if count != expected_hours:
            report.issues.append(f"{city}: {count} hourly rows, expected {expected_hours}")

    for column in POLLUTANT_COLUMNS:
        if column in frame and (frame[column] < 0).any():
            report.issues.append(f"negative values in {column}")

    null_share = frame["pm2_5"].isna().mean()
    if null_share > 0.25:
        report.issues.append(f"pm2_5 is {null_share:.0%} null")

    return report
