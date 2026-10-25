"""Download the already-validated BahnPulse September 2026 pilot snapshot.

This is a convenience function for reproducing the public static preview locally.
The authoritative raw source and full rebuild steps are in README.md.
"""
from __future__ import annotations
import gzip
import json
import urllib.request
from pathlib import Path

URL = 'https://bahn-pulse.vercel.app/data.json.gz'
DEST = Path(__file__).resolve().parents[1] / 'web' / 'data.json.gz'


def download():
    req = urllib.request.Request(URL, headers={'User-Agent':'BahnPulseLocalPilot/1.0'})
    with urllib.request.urlopen(req, timeout=45) as response:
        body = response.read(1_000_000)
    obj = json.loads(gzip.decompress(body))
    if obj.get('period') != '2026-09' or obj.get('summary',{}).get('scheduled',0) < 1_000_000:
        raise ValueError('Unexpected or incomplete BahnPulse dataset')
    DEST.write_bytes(body)
    return DEST


if __name__ == '__main__':
    print('Validated pilot data downloaded to', download())
