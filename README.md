# BahnPulse — Germany's Rail Reliability Explorer

[Live dashboard](https://bahn-pulse.vercel.app/) · [Source archive](https://huggingface.co/datasets/piebro/deutsche-bahn-data) · [Methodology](PROJECT_SCOPE.md) · [Monthly data refresh](.github/workflows/refresh.yml)

**BahnPulse is an independent, free, reproducible data analytics portfolio project.** The interactive site explores historical train delays, cancellations, rail categories, station-level reliability, and weekday/hourly patterns, using Deutsche Bahn API observations archived by Piet Brömmel. The first verified reporting month is **September 2026**.

## What the dashboard shows

- Train-stop delay share (six minutes or longer) and cancellation share, each with its correct denominator.
- Historical arrival observations and railway station coverage.
- Selectable high-volume station profiles, hour-by-hour differences, train-category comparisons and a weekday/hour heatmap.
- Sample sizes, precise definitions, attribution, and limitations prominently displayed.

These are **scheduled train-stop observations**, not whole journeys, passengers or the official DB on-time KPI. The station explorer intentionally offers a curated selection, not every station in the source archive. The current report contains **one month** of data; seasonality, line-level journey tracking, weather analysis, construction causes and a prediction model are future work, not currently available features.

## Data source and validation

- Source: [Piet Brömmel's Deutsche Bahn Data](https://huggingface.co/datasets/piebro/deutsche-bahn-data), based on Deutsche Bahn's public timetable APIs, source attribution CC BY 4.0.
- Raw file: `monthly_processed_data/data-2026-09.parquet`, 358,652,373 bytes, about 14.8 million unfiltered stop records.
- Initial filtered analysis: 13,278,301 scheduled rail arrival observations, 2,056,289 arrivals six minutes or more late out of 12,811,180 non-canceled observed arrivals, and 467,121 canceled scheduled arrivals.
- Delay is measured from the *arrival-specific* changed versus planned timestamp, not the archive's generic `delay_in_min` field. The last reported time may not always be a confirmed physical arrival.
- Excludes additional unscheduled stops and bus services. Count comparisons are not adjusted for station size, operator mix, or API collection gaps.
- Not all stations have a complete observation history; the source archive expanded coverage in late 2025.

## Run the website locally

```bash
git clone https://github.com/hjsarker/bahn-pulse.git
cd bahn-pulse
python3 -m http.server 8000 --directory web
# open http://localhost:8000
```

The repository includes the compact validated `web/data.json.gz` snapshot, so this works offline once the files have been cloned. The live dashboard first checks this public GitHub repo for fresh data; if the request fails, it falls back to the bundled Vercel copy.

## Reproduce the statistics

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q
python3 -m pipeline.refresh --check
```

To rebuild manually, download a source month (`data-YYYY-MM.parquet`) from the [archive](https://huggingface.co/datasets/piebro/deutsche-bahn-data/tree/main/monthly_processed_data) and run:

```bash
python3 -m pipeline.build_data --parquet data/data-2026-09.parquet --out data/dashboard.json
python3 -c "import gzip,pathlib; p=pathlib.Path('data/dashboard.json');pathlib.Path('web/data.json.gz').write_bytes(gzip.compress(p.read_bytes(),compresslevel=9))"
```

The pipeline reads Parquet with DuckDB SQL window/aggregate capabilities, computes category/station/hour/week aggregates and checks denominators. Raw Parquet files and intermediate JSON output are excluded from the repository to avoid hundreds of megabytes in Git history.

## Free automated refresh

The [GitHub Actions monthly workflow](.github/workflows/refresh.yml) checks the archive on the **5th and 15th of every month at 08:17 German time**, processes a new *completed* month only if published, validates the dataset and commits the compact snapshot. It does **not** pay for external APIs or deploy a dynamic backend. Public-repository standard GitHub-hosted runners are free under GitHub's public-repo policy. Large upstream downloads (~350 MB per new month) still consume job time and are subject to the data publisher's availability and bandwidth rules.

Scheduled automation is not a real-time feed. The first actual run must be checked under GitHub Actions, and upstream schema or access changes can require maintenance. The dashboard reads the current validated compressed JSON from this repository, so routine *data* updates do not require redeploying the Vercel frontend. Website-code changes do require a new deployment.

CI runs six deterministic tests, validates the packaged data and checks frontend JavaScript syntax. The pipeline will refuse inconsistent source data; it never substitutes invented numbers.

## Technology and next milestones

**Python · DuckDB · Parquet · GitHub Actions · pytest · HTML/CSS/JavaScript · static hosting**

Next: multi-month series with consistent coverage, all-station discovery, validated origin/destination analysis, weather correlation with DWD, and only then a calibrated delay-risk model with time-based validation. See [PROJECT_SCOPE.md](PROJECT_SCOPE.md).

## Licence

Original application code MIT (see [LICENSE](LICENSE)). Source railway data retains the upstream publishers' terms and CC BY 4.0 attribution; MIT does **not** relicense DB data.