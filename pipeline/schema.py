"""Quality checks for published BahnPulse stop-level aggregate snapshots."""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path


def validate(payload: dict) -> None:
    period = payload.get("period", "")
    if not re.fullmatch(r"20\d{2}-(?:0[1-9]|1[0-2])", period):
        raise ValueError(f"Invalid reporting period: {period!r}")
    summary = payload.get("summary", {})
    scheduled = summary.get("scheduled", 0)
    canceled = summary.get("canceled", -1)
    operated = summary.get("operated", -1)
    late6 = summary.get("late6", -1)
    late15 = summary.get("late15", -1)
    if not (isinstance(scheduled, int) and scheduled >= 500_000):
        raise ValueError("Unexpectedly few scheduled arrival observations")
    if not (0 <= canceled <= scheduled and 0 < operated <= scheduled - canceled):
        raise ValueError("Invalid cancellation or observed arrival denominator")
    if not 0 <= late15 <= late6 <= operated:
        raise ValueError("Impossible late-arrival counts")
    if payload.get("record_unit") != "scheduled arrival stop":
        raise ValueError("Unexpected observation unit")
    if len(payload.get("heatmap", [])) != 7 * 24:
        raise ValueError("Incomplete weekday/hour heatmap")
    if len(payload.get("stations", [])) < 20:
        raise ValueError("Station explorer coverage unexpectedly low")
    if payload.get("quality", {}).get("total_stations", 0) < 500:
        raise ValueError("Too few source stations")
    if any(v.get("operated", 0) < v.get("late6", 0) for v in payload["stations"]):
        raise ValueError("Invalid station-level late counts")


def from_gzip(path: Path) -> dict:
    obj = json.loads(gzip.decompress(path.read_bytes()))
    validate(obj)
    return obj
