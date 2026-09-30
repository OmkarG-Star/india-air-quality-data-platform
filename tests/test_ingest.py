from datetime import date

import pandas as pd

from aqp.ingest import _date_range, run_day
from aqp.storage import bronze_path, raw_path
from tests.conftest import FakeClient

DAY = date(2026, 9, 29)


def test_run_day_writes_raw_and_bronze(tmp_path, config, sample_payload):
    client = FakeClient(sample_payload)
    assert run_day(DAY, config, client, data_dir=tmp_path)

    assert raw_path(tmp_path, DAY, "pune").exists()
    assert raw_path(tmp_path, DAY, "mumbai").exists()
    bronze = pd.read_parquet(bronze_path(tmp_path, DAY))
    assert len(bronze) == 48
    assert set(bronze["city"]) == {"Pune", "Mumbai"}


def test_rerun_is_idempotent(tmp_path, config, sample_payload):
    client = FakeClient(sample_payload)
    run_day(DAY, config, client, data_dir=tmp_path)
    run_day(DAY, config, client, data_dir=tmp_path)
    assert len(pd.read_parquet(bronze_path(tmp_path, DAY))) == 48


def test_one_city_failing_does_not_block_others(tmp_path, config, sample_payload):
    client = FakeClient(sample_payload, fail_for={"Mumbai"})
    ok = run_day(DAY, config, client, data_dir=tmp_path)

    assert ok is False  # the day is reported as incomplete...
    bronze = pd.read_parquet(bronze_path(tmp_path, DAY))
    assert set(bronze["city"]) == {"Pune"}  # ...but Pune still loads


def test_strict_mode_blocks_bad_data(tmp_path, config, sample_payload):
    sample_payload["hourly"]["pm2_5"][0] = -1
    client = FakeClient(sample_payload)
    assert run_day(DAY, config, client, data_dir=tmp_path, strict=True) is False
    assert not bronze_path(tmp_path, DAY).exists()


def test_date_range_is_inclusive():
    days = _date_range(date(2026, 9, 1), date(2026, 9, 3))
    assert days == [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3)]
