"""
scripts/build_sqlite_db.py

Loads the live dashboard-ready CSVs into a single SQLite database, so the
data can be queried with SQL (e.g. by the text-to-sql-agent-eval project)
instead of only being read as flat CSVs.

Run this as the LAST step of the pipeline, after build_dashboard_data.py:
    python scripts/live_status_logger.py --once
    python scripts/fetch_economic_data.py
    python scripts/build_dashboard_data.py
    python scripts/build_sqlite_db.py

Add data/london_transport.db to the same `git add data/` commit step in
your GitHub Actions workflows so it stays live alongside the CSVs.
"""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "london_transport.db"

# table_name -> source CSV. Table names are capitalized to match the
TABLES = {
    "LineStatus":        "all_lines_combined.csv",         # current status, every line
    "Disruption":        "disruption_enriched.csv",         # current disruptions + cause
    "BoroughSummary":    "borough_disruption_summary.csv",  # one row per borough, now
    "BoroughDailyTrend": "borough_disruption_daily.csv",    # borough x day, growing history
    "DisruptionCause":   "disruption_cause_summary.csv",    # incidents grouped by cause
    "ModeSummary":       "mode_disruption_summary.csv",     # one row per transport mode
    "BoroughRisk":       "forecast_disruption_risk.csv",    # risk score + est. GVA at risk
}


def dedupe_columns_case_insensitive(df: pd.DataFrame) -> pd.DataFrame:
    """
    SQLite treats column names case-insensitively, so a CSV with both
    'borough' and 'Borough' (e.g. borough_disruption_daily.csv, where the
    economic merge keeps both the groupby key and the join key) fails at
    CREATE TABLE with 'duplicate column name'. Keep the first occurrence
    of each name (case-insensitive) and drop the rest.
    """
    seen = set()
    keep = []
    for col in df.columns:
        key = col.lower()
        if key not in seen:
            seen.add(key)
            keep.append(col)
    dropped = set(df.columns) - set(keep)
    if dropped:
        print(f"    (dropped duplicate-name column(s): {sorted(dropped)})")
    return df[keep]


def main():
    con = sqlite3.connect(DB_PATH)
    loaded = {}

    for table, filename in TABLES.items():
        path = DATA_DIR / filename
        if not path.exists():
            print(f"  ⚠ Skipping {table}: {filename} not found "
                  f"(run build_dashboard_data.py first)")
            continue
        df = pd.read_csv(path)
        df = dedupe_columns_case_insensitive(df)
        df.to_sql(table, con, if_exists="replace", index=False)
        loaded[table] = len(df)
        print(f"  ✓ {table:<18} ← {filename}  ({len(df)} rows)")

    con.commit()
    con.close()

    if loaded:
        print(f"\n✅ {DB_PATH.name} built with {len(loaded)} tables.")
    else:
        print("\n⚠ No tables were loaded — run the earlier pipeline steps first.")


if __name__ == "__main__":
    main()
