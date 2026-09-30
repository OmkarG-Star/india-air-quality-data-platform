import pytest

from aqp.config import DEFAULT_CONFIG, load_config


def test_default_config_loads():
    config = load_config(DEFAULT_CONFIG)
    assert len(config.cities) >= 8
    assert "pm2_5" in config.hourly_variables
    assert config.timezone == "Asia/Kolkata"


def test_rejects_bad_coordinates(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "cities:\n  - {name: X, state: Y, latitude: 123, longitude: 10}\nhourly_variables: [pm2_5]\n"
    )
    with pytest.raises(ValueError, match="Invalid coordinates"):
        load_config(bad)


def test_rejects_duplicate_cities(tmp_path):
    dup = tmp_path / "dup.yaml"
    dup.write_text(
        "cities:\n"
        "  - {name: Pune, state: MH, latitude: 18.5, longitude: 73.8}\n"
        "  - {name: pune, state: MH, latitude: 18.5, longitude: 73.8}\n"
        "hourly_variables: [pm2_5]\n"
    )
    with pytest.raises(ValueError, match="unique"):
        load_config(dup)
