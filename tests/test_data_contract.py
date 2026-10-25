"""Small deterministic checks independent of downloading a 350 MB source file."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from pipeline.refresh import latest_completed_month
from pipeline.schema import validate, from_gzip


def sample():
    return {
        "period": "2026-09", "record_unit": "scheduled arrival stop",
        "summary": {"scheduled": 1_000_000, "canceled": 30_000, "operated": 970_000, "late6": 100_000, "late15": 35_000},
        "quality": {"total_stations": 1_200},
        "heatmap": [{"weekday": i // 24, "hour": i % 24} for i in range(168)],
        "stations": [{"station_name": f"Station {i}", "scheduled": 50_000, "operated": 49_000, "late6": 1_000} for i in range(22)]
    }


def test_valid_synthetic_snapshot():
    validate(sample())


def test_reject_invalid_denominators():
    obj = sample()
    obj["summary"]["late6"] = 2_000_000
    with pytest.raises(ValueError):
        validate(obj)


def test_reject_missing_hours():
    obj = sample()
    obj["heatmap"] = obj["heatmap"][:-1]
    with pytest.raises(ValueError):
        validate(obj)


def test_month_filter_excludes_incomplete_current_month():
    rows = [
        {"path": "monthly_processed_data/data-2026-09.parquet", "size": 358_652_373},
        {"path": "monthly_processed_data/data-2026-10.parquet", "size": 55_000_000},
    ]
    dt = datetime(2026, 10, 25, tzinfo=ZoneInfo("Europe/Berlin"))
    assert latest_completed_month(rows, dt) == "2026-09"


def test_gzip_snapshot(tmp_path):
    import gzip, json
    path = tmp_path / "data.json.gz"
    path.write_bytes(gzip.compress(json.dumps(sample()).encode()))
    assert from_gzip(path)["period"] == "2026-09"


def test_published_snapshot_if_present():
    from pathlib import Path
    path = Path("web/data.json.gz")
    if path.exists():
        assert from_gzip(path)["summary"]["scheduled"] > 500_000
