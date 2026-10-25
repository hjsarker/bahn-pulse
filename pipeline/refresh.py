"""Safely refresh the BahnPulse pilot from the latest published monthly Parquet.

Runs only when the upstream archive has published a *completed* calendar month
newer than the bundled data. No paid API, browser automation or API key.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip
import json
import os
import re
import shutil
import tempfile
import urllib.request
from pathlib import Path

from pipeline.build_data import build
from pipeline.schema import from_gzip, validate

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "web" / "data.json.gz"
LIST_URL = "https://huggingface.co/api/datasets/piebro/deutsche-bahn-data/tree/main/monthly_processed_data?limit=100"
PARQUET_URL = "https://huggingface.co/datasets/piebro/deutsche-bahn-data/resolve/main/monthly_processed_data/data-{month}.parquet"
MONTH_PATTERN = re.compile(r"data-(20\d{2}-(?:0[1-9]|1[0-2]))\.parquet$")


def latest_completed_month(entries: list[dict], now: datetime | None = None) -> str:
    now = now or datetime.now(ZoneInfo("Europe/Berlin"))
    current_month = f"{now.year:04d}-{now.month:02d}"
    candidates = []
    for item in entries:
        match = MONTH_PATTERN.search(item.get("path", ""))
        if match and match.group(1) < current_month and item.get("size", 0) >= 10_000_000:
            candidates.append(match.group(1))
    if not candidates:
        raise ValueError("No complete, sufficiently sized Parquet month in the source listing")
    return max(candidates)


def load_listing() -> list[dict]:
    request = urllib.request.Request(LIST_URL, headers={"User-Agent": "BahnPulse/1.0 (research demo)"})
    with urllib.request.urlopen(request, timeout=35) as response:
        data = json.load(response)
    if not isinstance(data, list):
        raise ValueError("Unexpected source listing response")
    return data


def download_month(month: str, target: Path) -> None:
    request = urllib.request.Request(PARQUET_URL.format(month=month), headers={"User-Agent": "BahnPulse/1.0 (research demo)"})
    with urllib.request.urlopen(request, timeout=90) as response, target.open("wb") as stream:
        # Upper bound guards against accidentally fetching a vast, unexpected file.
        transferred = 0
        while (part := response.read(4 * 1024 * 1024)):
            transferred += len(part)
            if transferred > 2_000_000_000:
                raise ValueError("Parquet file exceeds safety limit")
            stream.write(part)
    if transferred < 10_000_000:
        raise ValueError(f"Source month {month} is incomplete ({transferred} bytes)")
    with target.open("rb") as stream:
        if stream.read(4) != b"PAR1":
            raise ValueError("Not a Parquet file")


def refresh() -> dict:
    previous = from_gzip(SNAPSHOT) if SNAPSHOT.exists() else None
    latest = latest_completed_month(load_listing())
    if previous and latest <= previous["period"]:
        return {"status": "unchanged", "month": previous["period"], "scheduled": previous["summary"]["scheduled"]}

    with tempfile.TemporaryDirectory(prefix="bahnpulse-") as folder:
        temp = Path(folder)
        parquet_path = temp / f"data-{latest}.parquet"
        json_path = temp / "dashboard.json"
        download_month(latest, parquet_path)
        payload = build(parquet_path, json_path, latest)
        validate(payload)
        zipped = gzip.compress(json_path.read_bytes(), compresslevel=9)
        # Verify all serialized data before replacing the public snapshot.
        test_path = temp / "data.json.gz"
        test_path.write_bytes(zipped)
        from_gzip(test_path)
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        os.replace(test_path, SNAPSHOT)
        return {"status": "updated", "month": latest, "scheduled": payload["summary"]["scheduled"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Validate the existing snapshot without network access")
    args = parser.parse_args()
    if args.check:
        snapshot = from_gzip(SNAPSHOT)
        print(json.dumps({"status": "valid", "month": snapshot["period"], "scheduled": snapshot["summary"]["scheduled"]}))
    else:
        print(json.dumps(refresh()))


if __name__ == "__main__":
    main()
