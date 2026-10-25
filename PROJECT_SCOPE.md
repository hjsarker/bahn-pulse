# BahnPulse — Scope and next iteration

## Completed in the September 2026 proof of concept
- Verified live Hugging Face source, downloaded full 2026-09 Parquet month (358,652,373 bytes), inspected its current schema.
- Processed 14,765,419 raw stop rows, and filtered to 13,278,301 scheduled arrival-stop observations for an explicitly defined study population.
- Measured 2,056,289 late (>=6 minutes) of 12,811,180 observed non-canceled arrivals; 467,121 canceled out of 13,278,301 scheduled arrival stops.
- Analyzed the source's 5,179 distinct station names, selected high-volume station profiles, 24-hour x 7-day heatmap and train-type categories.
- Built and published a separate static Vercel pilot with real precomputed aggregates. Source code is downloadable, not yet published in a dedicated GitHub repository.

## Next iteration
1. **Data quality:** identify archival collection gaps, outlier treatment and station identifiers; harmonize months affected by upstream reprocessing.
2. **Multimonth trends:** ingest 2026 months with consistent coverage; create partition-aware DuckDB queries and monthly aggregation snapshots.
3. **Station/line explorer:** search all stations and group lines by service + station corridor, not unqualified line number.
4. **Journeys/routes:** derive matched train rides and paired origin/destination stops from `train_line_ride_id`, then measure journey delay and missed connections; validate ID continuity.
5. **Weather:** integrate historical DWD weather, station geolocation and planned time; avoid false cause claims.
6. **ML:** calibrated binary outcome model with chronological validation and leakage checks; only if predictive signal exceeds simple baselines.
7. **Production automation:** automated schema checks, monitored monthly GitHub Actions, immutable snapshots, explicit last-ingested month and out-of-date badges.

## Caveats
This is a historical train-stop analysis; it does not prove the cause of individual disruptions, forecast live trains, or match Deutsche Bahn's official on-time KPI. It should not be marketed as a real-time arrival tracker.
