"""
data_integration.py  –  London Transport Reliability & Economic Impact

CHANGED: now reads data/tfl_status_history.csv (produced by
scripts/live_status_logger.py) instead of the three static manually-downloaded
snapshots (Status.csv, Status_all.csv, service_disruption.csv). Those files
and app.py are no longer part of the live pipeline — history accumulates
automatically every time the logger runs.

Produces the same Power-BI-ready file names as before (so dashboard.py and
your existing Power BI relationships keep working), plus two new files for
trend/time-series analysis.
"""
from pathlib import Path
import re
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

HISTORY_PATH     = DATA_DIR / "tfl_status_history.csv"   # NEW – growing live log
ECONOMIC_PATH    = DATA_DIR / "economic_data.csv"

OUT_COMBINED     = DATA_DIR / "all_lines_combined.csv"          # latest snapshot, enriched
OUT_DISRUPTION   = DATA_DIR / "disruption_enriched.csv"         # latest snapshot, disrupted only
OUT_MERGED       = DATA_DIR / "merged_transport_economic.csv"   # latest snapshot + economic data
OUT_SUMMARY      = DATA_DIR / "borough_disruption_summary.csv"  # latest-snapshot borough KPIs
OUT_HISTORY_ENRICHED = DATA_DIR / "all_lines_history_enriched.csv"  # NEW – full history, enriched
OUT_DAILY_SUMMARY    = DATA_DIR / "borough_disruption_daily.csv"    # NEW – borough KPIs per day (trend)

# ── Line → Borough mapping (unchanged) ─────────────────────────────────────────
LINE_TO_BOROUGH = {
    "Bakerloo":           "Westminster",
    "Central":            "Islington",
    "Circle":             "Westminster",
    "District":           "Westminster",
    "Hammersmith & City": "Westminster",
    "Jubilee":            "Westminster",
    "Metropolitan":       "Westminster",
    "Northern":           "Camden",
    "Piccadilly":         "Westminster",
    "Victoria":           "Westminster",
    "Waterloo & City":    "Westminster",
    "DLR":                "Tower Hamlets",
    "Elizabeth line":     "Westminster",
    "Liberty":            "Havering",
    "Lioness":            "Brent",
    "Mildmay":            "Hackney",
    "Suffragette":        "Waltham Forest",
    "Weaver":             "Tower Hamlets",
    "Windrush":           "Lambeth",
}

SEVERITY_LABELS = {
    1: "Special Service", 2: "Suspended", 3: "Part Suspended", 4: "Planned Closure",
    5: "Part Closure", 6: "Severe Delays", 7: "Reduced Service", 8: "Bus Service",
    9: "Minor Delays", 10: "Good Service", 11: "Part Closed", 12: "Exit Only",
    20: "No Step Free Access",
}

CAUSE_PATTERNS = {
    "Faulty Train":       r"faulty train",
    "Signal Failure":     r"signal failure",
    "Fire Alert":         r"fire alert",
    "Customer Incident":  r"customer incident",
    "Track Fault":        r"track fault|defective rail",
    "Staff Shortage":     r"staff shortage|shortage of (train )?crew",
    "Points Failure":     r"points failure",
    "Power Failure":      r"power failure|loss of traction power",
    "Strike":             r"strike|industrial action",
    "Flooding":           r"flooding|water ingress",
    "Planned Works":      r"planned engineering|scheduled maintenance",
    "Other":              r".*",
}


def classify_cause(reason: str) -> str:
    if pd.isna(reason) or not str(reason).strip():
        return "Unknown"
    text = str(reason).lower()
    for label, pattern in CAUSE_PATTERNS.items():
        if re.search(pattern, text):
            return label
    return "Other"


def normalize_borough(name: str) -> str:
    if pd.isna(name):
        return name
    return str(name).strip().replace(" City", "")


# ── Load + enrich the full history ──────────────────────────────────────────────
def load_and_enrich_history(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python scripts/live_status_logger.py --once` "
            "at least once before running data_integration.py."
        )
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.drop_duplicates(subset=["timestamp", "name"], keep="last")

    df["borough"]        = df["name"].map(LINE_TO_BOROUGH).fillna("Unknown")
    df["severity_label"] = df["statusSeverity"].map(SEVERITY_LABELS).fillna("Unknown")
    df["is_disrupted"]   = df["statusSeverity"] < 10
    df["disruption_cause"] = df["reason"].apply(classify_cause)
    df["affected_section"] = df["reason"].astype(str).str.extract(
        r"between (.+?) (?:due to|while|as)", flags=re.IGNORECASE
    )[0].str.strip()
    return df


def load_economic_data(path: Path) -> pd.DataFrame:
    econ = pd.read_csv(path)
    econ["Borough"] = econ["Borough"].apply(normalize_borough)
    return econ


def build_borough_economic_summary(econ: pd.DataFrame) -> pd.DataFrame:
    agg = {
        "Sales £m": "sum", "GVA £m": "sum", "Export Total £m": "sum",
        "Total Imports £m": "sum", "Number of companies": "sum",
        "Total Number of Employees": "sum",
        "Forecast Sales 2024/25": "mean", "Forecast Sales 2025/26": "mean",
        "Forecast Sales 2026/27": "mean", "Forecast Sales 2027/28": "mean",
        "Forecast Sales 2028/29": "mean",
    }
    available = {k: v for k, v in agg.items() if k in econ.columns}
    summary = econ.groupby("Borough", as_index=False).agg(available)
    return summary.rename(columns={
        "Sales £m": "total_sales_m", "GVA £m": "total_gva_m",
        "Export Total £m": "total_export_m", "Total Imports £m": "total_imports_m",
        "Number of companies": "total_companies",
        "Total Number of Employees": "total_employees",
        "Forecast Sales 2024/25": "forecast_sales_2024_25",
        "Forecast Sales 2025/26": "forecast_sales_2025_26",
        "Forecast Sales 2026/27": "forecast_sales_2026_27",
        "Forecast Sales 2027/28": "forecast_sales_2027_28",
        "Forecast Sales 2028/29": "forecast_sales_2028_29",
    })


def build_borough_summary(snapshot: pd.DataFrame, borough_econ: pd.DataFrame) -> pd.DataFrame:
    merged = snapshot.merge(borough_econ, left_on="borough", right_on="Borough", how="left")
    unmatched = merged[merged["Borough"].isna()]["borough"].unique()
    if len(unmatched):
        print(f"  ⚠ No economic data for boroughs: {unmatched}")

    summary = merged.groupby("borough", as_index=False).agg(
        lines_reported=("name", "nunique"),
        disrupted_lines=("is_disrupted", "sum"),
        average_severity=("statusSeverity", "mean"),
        total_sales_m=("total_sales_m", "first"),
        total_gva_m=("total_gva_m", "first"),
        total_employees=("total_employees", "first"),
        total_companies=("total_companies", "first"),
        forecast_sales_2024_25=("forecast_sales_2024_25", "first"),
        forecast_sales_2025_26=("forecast_sales_2025_26", "first"),
        forecast_sales_2026_27=("forecast_sales_2026_27", "first"),
        forecast_sales_2027_28=("forecast_sales_2027_28", "first"),
        forecast_sales_2028_29=("forecast_sales_2028_29", "first"),
    )
    summary["disruption_rate_pct"] = (
        summary["disrupted_lines"] / summary["lines_reported"] * 100
    ).round(1)
    return summary, merged


# ── Main pipeline ──────────────────────────────────────────────────────────────
def main():
    print("Loading + enriching live TfL history …")
    history = load_and_enrich_history(HISTORY_PATH)
    history.to_csv(OUT_HISTORY_ENRICHED, index=False)
    n_snapshots = history["timestamp"].nunique()
    print(f"  → {OUT_HISTORY_ENRICHED.name}: {len(history)} rows across "
          f"{n_snapshots} polls, {history['name'].nunique()} lines")

    # 1. Latest snapshot only — backward-compatible "current status" files
    latest_ts = history["timestamp"].max()
    latest = history[history["timestamp"] == latest_ts].copy()
    latest.to_csv(OUT_COMBINED, index=False)
    print(f"  → {OUT_COMBINED.name}: {len(latest)} rows (latest poll: {latest_ts})")

    disrupted_only = latest[latest["is_disrupted"]].copy()
    disrupted_only.to_csv(OUT_DISRUPTION, index=False)
    print(f"  → {OUT_DISRUPTION.name}: {len(disrupted_only)} disrupted service rows")

    # 2. Economic merge (economic data is static per-borough, so always uses latest snapshot)
    print("Loading economic data …")
    econ_df = load_economic_data(ECONOMIC_PATH)
    borough_econ = build_borough_economic_summary(econ_df)

    summary, merged_latest = build_borough_summary(latest, borough_econ)
    merged_latest.to_csv(OUT_MERGED, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    print(f"  → {OUT_MERGED.name}: {len(merged_latest)} rows")
    print(f"  → {OUT_SUMMARY.name}: {len(summary)} boroughs")

    # 3. NEW: daily borough summary across the FULL history — this is what gives
    #    correlation_analysis.py enough data points for meaningful statistics.
    daily = history.groupby(["date", "borough"], as_index=False).agg(
        lines_reported=("name", "nunique"),
        disrupted_lines=("is_disrupted", "sum"),
        average_severity=("statusSeverity", "mean"),
    )
    daily["disruption_rate_pct"] = (
        daily["disrupted_lines"] / daily["lines_reported"] * 100
    ).round(1)
    daily = daily.merge(borough_econ, left_on="borough", right_on="Borough", how="left")
    daily.to_csv(OUT_DAILY_SUMMARY, index=False)
    print(f"  → {OUT_DAILY_SUMMARY.name}: {len(daily)} borough-days "
          f"(across {history['date'].nunique()} calendar day(s) logged so far)")

    print("\n✅ Data integration complete.")
    print("Power BI / dashboard input files:")
    for f in [OUT_COMBINED, OUT_DISRUPTION, OUT_MERGED, OUT_SUMMARY,
              OUT_HISTORY_ENRICHED, OUT_DAILY_SUMMARY]:
        print(f"  {f}")


if __name__ == "__main__":
    main()
