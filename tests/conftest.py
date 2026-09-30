import json
from pathlib import Path

import pytest

from aqp.config import City, PipelineConfig

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_payload() -> dict:
    """Synthetic response shaped exactly like the Open-Meteo Air Quality API (tests only)."""
    return json.loads((FIXTURES / "open_meteo_pune_2026-09-29.json").read_text(encoding="utf-8"))


@pytest.fixture
def pune() -> City:
    return City("Pune", "Maharashtra", 18.5204, 73.8567)


@pytest.fixture
def config(pune) -> PipelineConfig:
    return PipelineConfig(
        cities=(pune, City("Mumbai", "Maharashtra", 19.0760, 72.8777)),
        hourly_variables=("pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide",
                          "sulphur_dioxide", "ozone", "us_aqi", "european_aqi"),
        timezone="Asia/Kolkata",
    )


class FakeClient:
    """Stands in for AirQualityClient so tests never touch the network."""

    def __init__(self, payload: dict, fail_for: set[str] | None = None):
        self.payload = payload
        self.fail_for = fail_for or set()
        self.calls = []

    def fetch_day(self, city, day, hourly_variables, timezone):
        self.calls.append((city.name, day))
        if city.name in self.fail_for:
            raise ConnectionError("simulated outage")
        return self.payload
