"""HTTP client for the Open-Meteo Air Quality API, with retries and timeouts."""

from __future__ import annotations

import logging
from datetime import date

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from aqp.config import City

logger = logging.getLogger(__name__)

BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def build_session(total_retries: int = 5, backoff_factor: float = 1.0) -> requests.Session:
    """Session that retries transient failures (429 / 5xx) with exponential backoff."""
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "india-air-quality-data-platform/0.1"})
    return session


class AirQualityClient:
    def __init__(self, session: requests.Session | None = None, timeout: float = 30.0):
        self.session = session or build_session()
        self.timeout = timeout

    def fetch_day(
        self,
        city: City,
        day: date,
        hourly_variables: tuple[str, ...],
        timezone: str,
    ) -> dict:
        """Fetch 24 hourly observations for one city and one day."""
        params = {
            "latitude": city.latitude,
            "longitude": city.longitude,
            "hourly": ",".join(hourly_variables),
            "timezone": timezone,
            "start_date": day.isoformat(),
            "end_date": day.isoformat(),
        }
        logger.info("Fetching %s for %s", city.name, day)
        response = self.session.get(BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()

        if "hourly" not in payload or "time" not in payload["hourly"]:
            raise ValueError(f"Unexpected response for {city.name}: missing 'hourly.time'")
        return payload
