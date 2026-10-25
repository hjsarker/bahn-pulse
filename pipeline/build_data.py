"""Generate a compact BahnPulse pilot snapshot from one archived DB stop-data Parquet month.

Usage:
    pip install duckdb
    python -m pipeline.build_data --parquet data-2026-09.parquet --out data/dashboard.json

The processed archive consists of train *stop* observations, not individual journeys.
Delay is arrival_change_time minus arrival_planned_time, in minutes.
Canceled arrivals are excluded from the delay denominator and reported separately.
"""
from __future__ import annotations
import argparse
import json
from datetime import date
from pathlib import Path

SOURCE_URL = "https://huggingface.co/datasets/piebro/deutsche-bahn-data"
TRAIN_TYPES = ["ICE", "IC", "EC", "RE", "RB", "S"]
FEATURED = ["Dortmund Hbf", "Essen Hbf", "Düsseldorf Hbf", "Duisburg Hbf", "Köln Hbf", "Köln Messe/Deutz", "Bonn Hbf", "Bochum Hbf", "Wuppertal Hbf", "Münster (Westf) Hbf", "Berlin Hbf", "Berlin Ostkreuz", "Hamburg Hbf", "Frankfurt (Main) Hbf", "München Hbf", "Stuttgart Hbf", "Leipzig Hbf", "Dresden Hbf", "Hannover Hbf", "Nürnberg Hbf"]

BASE = """
    count(*) AS scheduled,
    count(*) FILTER (WHERE canceled) AS canceled,
    count(*) FILTER (WHERE NOT canceled AND deviation IS NOT NULL) AS operated,
    count(*) FILTER (WHERE NOT canceled AND deviation >= 6) AS late6,
    count(*) FILTER (WHERE NOT canceled AND deviation >= 15) AS late15,
    round(avg(deviation) FILTER (WHERE NOT canceled), 2) AS mean_delay
"""

def build(parquet: Path, out: Path, report_month: str | None = None) -> dict:
    import duckdb
    if not parquet.is_file():
        raise FileNotFoundError(parquet)
    filename = parquet.name
    period = report_month or filename.removeprefix('data-').removesuffix('.parquet')
    year, month = (int(x) for x in period.split('-'))
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    sql_parquet = str(parquet.absolute()).replace("'", "''")
    db = duckdb.connect()
    db.execute('PRAGMA threads=2')
    db.execute(f"""
    CREATE TEMP TABLE events AS
    SELECT station_name,
           eva,
           train_type,
           line_number,
           arrival_planned_time AS planned,
           extract(hour FROM arrival_planned_time)::INT AS hour,
           (extract(isodow FROM arrival_planned_time)::INT - 1) AS weekday,
           coalesce(arrival_is_canceled, FALSE) AS canceled,
           date_diff('minute', arrival_planned_time, arrival_change_time) AS deviation
    FROM read_parquet('{sql_parquet}')
    WHERE arrival_planned_time >= '{start}' AND arrival_planned_time < '{end}'
      AND coalesce(has_plan_record, FALSE)
      AND NOT coalesce(is_additional_stop, FALSE)
      AND station_name IS NOT NULL
      AND train_type <> 'Bus'
    """)
    def rows(query):
        cursor = db.execute(query)
        fields = [v[0] for v in cursor.description]
        return [dict(zip(fields, rec)) for rec in cursor.fetchall()]

    summary = rows('SELECT '+BASE+' FROM events')[0]
    by_type = rows(f'SELECT train_type, {BASE} FROM events GROUP BY 1 HAVING count(*) >= 5000 ORDER BY scheduled DESC LIMIT 22')
    hours = rows(f'SELECT hour, {BASE} FROM events GROUP BY 1 ORDER BY hour')
    weekdays = rows(f'SELECT weekday, {BASE} FROM events GROUP BY 1 ORDER BY weekday')
    heatmap = rows(f'SELECT weekday, hour, {BASE} FROM events GROUP BY 1,2 ORDER BY weekday,hour')
    top_stations = rows(f'SELECT station_name, {BASE} FROM events GROUP BY 1 ORDER BY scheduled DESC LIMIT 70')
    def sql_text(v): return "'"+v.replace("'", "''")+"'"
    named_stations = rows(f'SELECT station_name, {BASE} FROM events WHERE station_name IN ({",".join(map(sql_text,FEATURED))}) GROUP BY 1 ORDER BY scheduled DESC')
    all_stations = {s['station_name']:s for s in top_stations + named_stations}
    stations = sorted(all_stations.values(), key=lambda p:p['scheduled'], reverse=True)
    stations_for_heat = [s['station_name'] for s in named_stations if s['scheduled'] >= 2500]
    station_hours = rows(f'SELECT station_name, hour, {BASE} FROM events WHERE station_name IN ({",".join(map(sql_text,stations_for_heat))}) GROUP BY 1,2 ORDER BY 1,2')
    station_weekdays = rows(f'SELECT station_name, weekday, {BASE} FROM events WHERE station_name IN ({",".join(map(sql_text,stations_for_heat))}) GROUP BY 1,2 ORDER BY 1,2')
    monthly_quality = rows("""SELECT count(*) AS unique_stop_rows, count(DISTINCT station_name) AS total_stations,
      count(DISTINCT eva) AS station_evas, count(DISTINCT train_type) AS types,
      min(planned)::VARCHAR AS first_planned,
      max(planned)::VARCHAR AS last_planned,
      count(*) FILTER (WHERE deviation IS NULL AND NOT canceled) AS unknown_arrival_deviation,
      count(*) FILTER (WHERE deviation > 360 OR deviation < -120) AS extreme_deviation
      FROM events""")[0]
    data = {'name':'BahnPulse', 'period':period, 'record_unit':'scheduled arrival stop',
      'source':{'name':'Piet Brömmel / Deutsche Bahn Data', 'url':SOURCE_URL,
        'file':f'monthly_processed_data/{filename}', 'license':'CC BY 4.0',
        'record_timezone':'Europe/Berlin'},
      'methodology':{'late_threshold_minutes':6,
        'delay_metric':'arrival_change_time minus arrival_planned_time, minutes',
        'denominator':'non-canceled scheduled arrivals with known arrival-time deviation',
        'canceled_rate_denominator':'all scheduled arrival stops',
        'coverage':'recorded station arrivals, excludes additional unscheduled stops and buses',
        'warning':'Not official DB punctuality: stop-level records, partial coverage, reporting/API changes and latest change times may not always be verified actual arrivals.'},
      'summary':summary, 'quality':monthly_quality, 'train_types':by_type,
      'hours':hours, 'weekdays':weekdays, 'heatmap':heatmap,
      'stations':stations, 'station_hours':station_hours, 'station_weekdays':station_weekdays}
    if not data['summary']['operated'] or data['summary']['scheduled'] < 500000:
        raise ValueError('Insufficient observed arrivals')
    if len(data['heatmap']) < 130 or len(data['stations']) < 20:
        raise ValueError('Missing time-grid or station coverage')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n",encoding='utf-8')
    db.close()
    return data

if __name__=='__main__':
    cli=argparse.ArgumentParser()
    cli.add_argument('--parquet',type=Path,required=True)
    cli.add_argument('--out',type=Path,default=Path('data/dashboard.json'))
    cli.add_argument('--month',type=str)
    a=cli.parse_args()
    result=build(a.parquet,a.out,a.month)
    print('Saved',a.out,'rows:',result['summary']['scheduled'],'stations featured:',len(result['stations']))
