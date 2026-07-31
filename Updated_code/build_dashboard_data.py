"""
scripts/build_dashboard_data.py

Consolidates the old data_integration.py + correlation_analysis.py into one
file, and reads ONLY live-fetched data:
  - data/tfl_status_history.csv       (from live_status_logger.py)
  - data/borough_economic_live.csv    (from fetch_economic_data.py)

No manually-downloaded files are read anywhere in this pipeline.

Keeps the parts of the old scripts you said you still want: line→borough
mapping, severity labelling, disruption-cause classification, borough risk
scoring, and Pearson correlation — just in one clean file instead of two.

Run this after both fetch scripts have produced their inputs:
    python scripts/live_status_logger.py --once
    python scripts/fetch_economic_data.py
    python scripts/build_dashboard_data.py
"""
from pathlib import Path
import re
import pandas as pd
from scipy.stats import pearsonr

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

HISTORY_PATH  = DATA_DIR / "tfl_status_history.csv"       # live — TfL API
ECONOMIC_PATH = DATA_DIR / "borough_economic_live.csv"     # live — ONS API

OUT_COMBINED         = DATA_DIR / "all_lines_combined.csv"
OUT_DISRUPTION       = DATA_DIR / "disruption_enriched.csv"
OUT_MERGED           = DATA_DIR / "merged_transport_economic.csv"
OUT_SUMMARY          = DATA_DIR / "borough_disruption_summary.csv"
OUT_HISTORY_ENRICHED = DATA_DIR / "all_lines_history_enriched.csv"
OUT_DAILY_SUMMARY    = DATA_DIR / "borough_disruption_daily.csv"
OUT_CAUSE            = DATA_DIR / "disruption_cause_summary.csv"
OUT_MODE             = DATA_DIR / "mode_disruption_summary.csv"
OUT_FORECAST         = DATA_DIR / "forecast_disruption_risk.csv"   # name kept for
                                                                     # dashboard/PowerBI
                                                                     # compatibility;
                                                                     # "forecast" now
                                                                     # means risk score,
                                                                     # not sales forecast
OUT_REPORT           = DATA_DIR / "correlation_report.txt"

# ── Line → Borough mapping ──────────────────────────────────────────────────────
LINE_TO_BOROUGH = {
    "Bakerloo": "Westminster", "Central": "Islington", "Circle": "Westminster",
    "District": "Westminster", "Hammersmith & City": "Westminster",
    "Jubilee": "Westminster", "Metropolitan": "Westminster", "Northern": "Camden",
    "Piccadilly": "Westminster", "Victoria": "Westminster",
    "Waterloo & City": "Westminster", "DLR": "Tower Hamlets",
    "Elizabeth line": "Westminster", "Liberty": "Havering", "Lioness": "Brent",
    "Mildmay": "Hackney", "Suffragette": "Waltham Forest", "Weaver": "Tower Hamlets",
    "Windrush": "Lambeth",
}

SEVERITY_LABELS = {
    1: "Special Service", 2: "Suspended", 3: "Part Suspended", 4: "Planned Closure",
    5: "Part Closure", 6: "Severe Delays", 7: "Reduced Service", 8: "Bus Service",
    9: "Minor Delays", 10: "Good Service", 11: "Part Closed", 12: "Exit Only",
    20: "No Step Free Access",
}

CAUSE_PATTERNS = {
    "Faulty Train": r"faulty train", "Signal Failure": r"signal failure",
    "Fire Alert": r"fire alert", "Customer Incident": r"customer incident",
    "Track Fault": r"track fault|defective rail",
    "Staff Shortage": r"staff shortage|shortage of (train )?crew",
    "Points Failure": r"points failure",
    "Power Failure": r"power failure|loss of traction power",
    "Strike": r"strike|industrial action", "Flooding": r"flooding|water ingress",
    "Planned Works": r"planned engineering|scheduled maintenance", "Other": r".*",
}


def classify_cause(reason: str) -> str:
    if pd.isna(reason) or not str(reason).strip():
        return "Unknown"
    text = str(reason).lower()
    for label, pattern in CAUSE_PATTERNS.items():
        if re.search(pattern, text):
            return label
    return "Other"


def pearson_safe(x: pd.Series, y: pd.Series):
    valid = pd.concat([x, y], axis=1).dropna()
    if len(valid) < 2:
        return None, None
    return pearsonr(valid.iloc[:, 0], valid.iloc[:, 1])


# ── Load + enrich the live TfL history ──────────────────────────────────────────
def load_and_enrich_history(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python updated_code/live_status_logger.py --once` first."
        )
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.drop_duplicates(subset=["timestamp", "name"], keep="last")
    df["borough"] = df["name"].map(LINE_TO_BOROUGH).fillna("Unknown")
    df["severity_label"] = df["statusSeverity"].map(SEVERITY_LABELS).fillna("Unknown")
    df["is_disrupted"] = df["statusSeverity"] < 10
    df["disruption_cause"] = df["reason"].apply(classify_cause)
    df["affected_section"] = df["reason"].astype(str).str.extract(
        r"between (.+?) (?:due to|while|as)", flags=re.IGNORECASE
    )[0].str.strip()
    return df


def load_live_economic(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python updated_code/fetch_economic_data.py` first."
        )
    return pd.read_csv(path)  # columns: Borough, total_gva_m, gva_year


def build_borough_summary(snapshot: pd.DataFrame, econ: pd.DataFrame):
    merged = snapshot.merge(econ, left_on="borough", right_on="Borough", how="left")
    print(f"  → Merged snapshot with economic data: {len(merged)} rows",merged.columns)
    unmatched = merged[merged["Borough"].isna()]["borough"].unique()
    if len(unmatched):
        print(f"  ⚠ No live economic data for boroughs: {unmatched}")

    summary = merged.groupby("borough", as_index=False).agg(
        lines_reported=("name", "nunique"),
        disrupted_lines=("is_disrupted", "sum"),
        average_severity=("statusSeverity", "mean"),
        total_gva_m=("total_gva_m", "first"),
    )
    summary["disruption_rate_pct"] = (
        summary["disrupted_lines"] / summary["lines_reported"] * 100
    ).round(1)
    return summary, merged


def main():
    print("Loading + enriching live TfL history …")
    history = load_and_enrich_history(HISTORY_PATH)
    history.to_csv(OUT_HISTORY_ENRICHED, index=False)
    n_snapshots = history["timestamp"].nunique()
    print(f"  → {OUT_HISTORY_ENRICHED.name}: {len(history)} rows across "
          f"{n_snapshots} polls, {history['name'].nunique()} lines")

    latest_ts = history["timestamp"].max()
    latest = history[history["timestamp"] == latest_ts].copy()
    latest.to_csv(OUT_COMBINED, index=False)
    print(f"  → {OUT_COMBINED.name}: {len(latest)} rows (latest poll: {latest_ts})")

    disrupted_only = latest[latest["is_disrupted"]].copy()
    disrupted_only.to_csv(OUT_DISRUPTION, index=False)
    print(f"  → {OUT_DISRUPTION.name}: {len(disrupted_only)} disrupted service rows")

    print("Loading live ONS economic data …")
    econ = load_live_economic(ECONOMIC_PATH)

    summary, merged_latest = build_borough_summary(latest, econ)
    merged_latest.to_csv(OUT_MERGED, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)
    print(f"  → {OUT_MERGED.name}: {len(merged_latest)} rows")
    print(f"  → {OUT_SUMMARY.name}: {len(summary)} boroughs")

    # Daily borough summary across the FULL history — feeds trend charts and
    # gives the correlation step enough data points to be meaningful over time.
    daily = history.groupby(["date", "borough"], as_index=False).agg(
        lines_reported=("name", "nunique"),
        disrupted_lines=("is_disrupted", "sum"),
        average_severity=("statusSeverity", "mean"),
    )
    daily["disruption_rate_pct"] = (
        daily["disrupted_lines"] / daily["lines_reported"] * 100
    ).round(1)
    daily = daily.merge(econ, left_on="borough", right_on="Borough", how="left")
    daily.to_csv(OUT_DAILY_SUMMARY, index=False)
    print(f"  → {OUT_DAILY_SUMMARY.name}: {len(daily)} borough-days")

    # ── Cause + mode summaries ────────────────────────────────────────────────
    cause_counts = (
        disrupted_only.groupby("disruption_cause", as_index=False)
        .agg(incidents=("name", "count"), lines_affected=("name", "nunique"),
             avg_severity=("statusSeverity", "mean"))
        .sort_values("incidents", ascending=False)
    )
    cause_counts["severity_label"] = cause_counts["avg_severity"].apply(
        lambda s: "Severe" if s <= 6 else ("Moderate" if s <= 8 else "Minor")
    )
    cause_counts.to_csv(OUT_CAUSE, index=False)

    mode_summary = latest.groupby("modeName", as_index=False).agg(
        total_lines=("name", "nunique"), disrupted_lines=("is_disrupted", "sum"),
        avg_severity=("statusSeverity", "mean"),
    )
    mode_summary["disruption_rate_pct"] = (
        mode_summary["disrupted_lines"] / mode_summary["total_lines"] * 100
    ).round(1)
    mode_summary.to_csv(OUT_MODE, index=False)

    # ── Composite risk score + GVA at risk (latest snapshot) ──────────────────
    forecast = summary.copy()
    forecast["severity_risk"] = (10 - forecast["average_severity"]) / 9
    forecast["rate_risk"] = forecast["disruption_rate_pct"] / 100
    forecast["composite_risk_score"] = (
        0.6 * forecast["severity_risk"] + 0.4 * forecast["rate_risk"]
    ).round(3)
    forecast["risk_band"] = pd.cut(
        forecast["composite_risk_score"], bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
        labels=["Very Low", "Low", "Medium", "High", "Critical"],
    )
    forecast["estimated_gva_at_risk_m"] = (
        forecast["total_gva_m"] * forecast["composite_risk_score"] * 0.02
    ).round(2)
    forecast.to_csv(OUT_FORECAST, index=False)

    # ── Pearson correlations — latest snapshot AND full history ───────────────
    report_lines = ["London Transport – Correlation & Disruption Analysis", "=" * 60, ""]
    pairs = [
        ("average_severity", "total_gva_m", "Severity vs Borough GVA"),
        ("disruption_rate_pct", "total_gva_m", "Disruption Rate % vs GVA"),
    ]
    for df, label in [(summary, "latest snapshot only"), (daily, "full history, borough x day")]:
        report_lines.append(f"Pearson Correlations ({label}, n={len(df)}):")
        for col_a, col_b, name in pairs:
            r, p = pearson_safe(df[col_a], df[col_b])
            if r is not None:
                sig = "significant (p<0.05)" if p < 0.05 else "not yet significant"
                report_lines.append(f"  {name}: r={r:.3f}, p={p:.3f}  [{sig}]")
        report_lines.append("")

    report_text = "\n".join(report_lines)
    OUT_REPORT.write_text(report_text)
    print("\n" + report_text)

    print("✅ Pipeline complete. Dashboard/Power BI input files:")
    for f in [OUT_COMBINED, OUT_DISRUPTION, OUT_MERGED, OUT_SUMMARY,
              OUT_HISTORY_ENRICHED, OUT_DAILY_SUMMARY, OUT_CAUSE, OUT_MODE, OUT_FORECAST]:
        print(f"  {f}")


if __name__ == "__main__":
    main()
