"""Load and validate pipeline configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "cities.yaml"


@dataclass(frozen=True)
class City:
    name: str
    state: str
    latitude: float
    longitude: float

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" ", "_")


@dataclass(frozen=True)
class PipelineConfig:
    cities: tuple[City, ...]
    hourly_variables: tuple[str, ...]
    timezone: str


def load_config(path: Path | str = DEFAULT_CONFIG) -> PipelineConfig:
    """Read the YAML config and fail early on anything malformed."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    cities = []
    for item in raw.get("cities", []):
        lat, lon = float(item["latitude"]), float(item["longitude"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"Invalid coordinates for {item['name']}: {lat}, {lon}")
        cities.append(City(item["name"], item["state"], lat, lon))

    if not cities:
        raise ValueError("Config must list at least one city")

    slugs = [c.slug for c in cities]
    if len(slugs) != len(set(slugs)):
        raise ValueError("City names must be unique")

    variables = tuple(raw.get("hourly_variables", []))
    if not variables:
        raise ValueError("Config must list at least one hourly variable")

    return PipelineConfig(
        cities=tuple(cities),
        hourly_variables=variables,
        timezone=raw.get("timezone", "Asia/Kolkata"),
    )
