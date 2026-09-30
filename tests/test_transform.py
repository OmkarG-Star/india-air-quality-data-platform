from datetime import datetime

import pandas as pd

from aqp.transform import check_quality, to_bronze


def test_bronze_has_one_row_per_hour(sample_payload, pune):
    frame = to_bronze(sample_payload, pune, datetime(2026, 9, 30, 6, 0))
    assert len(frame) == 24
    assert frame["city"].unique().tolist() == ["Pune"]
    assert {"pm2_5", "pm10", "co", "no2", "so2", "o3", "us_aqi", "european_aqi"} <= set(frame.columns)
    assert pd.api.types.is_datetime64_any_dtype(frame["observed_at"])


def test_missing_variable_becomes_null_not_dropped(sample_payload, pune):
    del sample_payload["hourly"]["ozone"]
    frame = to_bronze(sample_payload, pune, datetime(2026, 9, 30))
    assert len(frame) == 24
    assert frame["o3"].isna().all()


def test_quality_passes_on_clean_data(sample_payload, pune):
    frame = to_bronze(sample_payload, pune, datetime(2026, 9, 30))
    assert check_quality(frame).passed


def test_quality_flags_duplicates_negatives_and_gaps(sample_payload, pune):
    frame = to_bronze(sample_payload, pune, datetime(2026, 9, 30))
    frame.loc[0, "pm10"] = -5
    frame = pd.concat([frame, frame.iloc[[1]]], ignore_index=True)

    issues = " | ".join(check_quality(frame).issues)
    assert "duplicate" in issues
    assert "negative values in pm10" in issues
    assert "25 hourly rows" in issues


def test_quality_flags_empty_frame():
    report = check_quality(pd.DataFrame())
    assert not report.passed
    assert report.issues == ["no rows"]
