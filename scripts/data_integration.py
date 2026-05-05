"""
data_integration.py  –  London Transport Reliability & Economic Impact
Merges ALL transport sources (Status.csv, Status_all.csv, service_disruption.csv)
with economic data and produces Power-BI-ready flat files.
"""
from pathlib import Path
import re
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

TRANSPORT_PATH   = DATA_DIR / "Status.csv"            # tube-only snapshot (used before)
STATUS_ALL_PATH  = DATA_DIR / "Status_all.csv"        # tube + DLR + Elizabeth + Overground
DISRUPTION_PATH  = DATA_DIR / "service_disruption.csv"  # detailed disruptions with reasons
ECONOMIC_PATH    = DATA_DIR / "economic_data.csv"

OUT_MERGED       = DATA_DIR / "merged_transport_economic.csv"
OUT_SUMMARY      = DATA_DIR / "borough_disruption_summary.csv"
OUT_DISRUPTION   = DATA_DIR / "disruption_enriched.csv"     # NEW – Power BI disruption table
OUT_COMBINED     = DATA_DIR / "all_lines_combined.csv"       # NEW – all modes unified

# ── Line → Borough mapping (expanded to cover all modes) ──────────────────────
LINE_TO_BOROUGH = {
    # Tube
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
    # DLR
    "DLR":                "Tower Hamlets",
    # Elizabeth line
    "Elizabeth line":     "Westminster",
    # Overground (new names since 2024)
    "Liberty":            "Havering",
    "Lioness":            "Brent",
    "Mildmay":            "Hackney",
    "Suffragette":        "Waltham Forest",
    "Weaver":             "Tower Hamlets",
    "Windrush":           "Lambeth",
}

# Severity → human-readable category
SEVERITY_LABELS = {
    1:  "Special Service",
    2:  "Suspended",
    3:  "Part Suspended",
    4:  "Planned Closure",
    5:  "Part Closure",
    6:  "Severe Delays",
    7:  "Reduced Service",
    8:  "Bus Service",
    9:  "Minor Delays",
    10: "Good Service",
    11: "Part Closed",
    12: "Exit Only",
    20: "No Step Free Access",
}

# ── Disruption-cause extraction ────────────────────────────────────────────────
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
    if pd.isna(reason) or not reason.strip():
        return "Unknown"
    text = reason.lower()
    for label, pattern in CAUSE_PATTERNS.items():
        if re.search(pattern, text):
            return label
    return "Other"


def normalize_borough(name: str) -> str:
    if pd.isna(name):
        return name
    return str(name).strip().replace(" City", "")


# ── Load helpers ───────────────────────────────────────────────────────────────
def load_transport_snapshot(path: Path, label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["source"] = label
    df["borough"] = df["name"].map(LINE_TO_BOROUGH).fillna("Unknown")
    df["severity_label"] = df["statusSeverity"].map(SEVERITY_LABELS).fillna("Unknown")
    df["is_disrupted"] = df["statusSeverity"] < 10
    return df


def load_disruption_detail(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["source"] = "service_disruption"
    df["borough"] = df["name"].map(LINE_TO_BOROUGH).fillna("Unknown")
    df["severity_label"] = df["statusSeverity"].map(SEVERITY_LABELS).fillna("Unknown")
    df["is_disrupted"] = df["statusSeverity"] < 10
    df["disruption_cause"] = df["reason"].apply(classify_cause)
    # Extract affected section from reason text
    df["affected_section"] = df["reason"].str.extract(
        r"between (.+?) (?:due to|while|as)", flags=re.IGNORECASE
    )[0].str.strip()
    return df


def load_economic_data(path: Path) -> pd.DataFrame:
    econ = pd.read_csv(path)
    econ["Borough"] = econ["Borough"].apply(normalize_borough)
    return econ


def build_borough_economic_summary(econ: pd.DataFrame) -> pd.DataFrame:
    agg = {
        "Sales £m":                "sum",
        "GVA £m":                  "sum",
        "Export Total £m":         "sum",
        "Total Imports £m":        "sum",
        "Number of companies":     "sum",
        "Total Number of Employees": "sum",
        "Forecast Sales 2024/25":  "mean",
        "Forecast Sales 2025/26":  "mean",
        "Forecast Sales 2026/27":  "mean",
        "Forecast Sales 2027/28":  "mean",
        "Forecast Sales 2028/29":  "mean",
    }
    available = {k: v for k, v in agg.items() if k in econ.columns}
    summary = econ.groupby("Borough", as_index=False).agg(available)
    summary = summary.rename(columns={
        "Sales £m":                  "total_sales_m",
        "GVA £m":                    "total_gva_m",
        "Export Total £m":           "total_export_m",
        "Total Imports £m":          "total_imports_m",
        "Number of companies":       "total_companies",
        "Total Number of Employees": "total_employees",
        "Forecast Sales 2024/25":    "forecast_sales_2024_25",
        "Forecast Sales 2025/26":    "forecast_sales_2025_26",
        "Forecast Sales 2026/27":    "forecast_sales_2026_27",
        "Forecast Sales 2027/28":    "forecast_sales_2027_28",
        "Forecast Sales 2028/29":    "forecast_sales_2028_29",
    })
    return summary


# ── Main pipeline ──────────────────────────────────────────────────────────────
def main():
    print("Loading transport data …")
    tube_df    = load_transport_snapshot(TRANSPORT_PATH,  "tube_snapshot")
    all_df     = load_transport_snapshot(STATUS_ALL_PATH, "status_all")
    disrupt_df = load_disruption_detail(DISRUPTION_PATH)

    # 1. Unified all-lines table (deduplication: prefer disruption detail if available)
    combined = pd.concat([all_df, disrupt_df], ignore_index=True)
    # Keep the disruption-detail row when a line appears in both
    combined = combined.sort_values("source").drop_duplicates(
        subset=["name", "date"], keep="last"
    ).reset_index(drop=True)
    combined.to_csv(OUT_COMBINED, index=False)
    print(f"  → {OUT_COMBINED.name}: {len(combined)} rows, {combined['name'].nunique()} lines")

    # 2. Disruption-enriched table (only disrupted rows with cause classification)
    disrupted_only = disrupt_df[disrupt_df["is_disrupted"]].copy()
    disrupted_only.to_csv(OUT_DISRUPTION, index=False)
    print(f"  → {OUT_DISRUPTION.name}: {len(disrupted_only)} disrupted service rows")

    # 3. Merge with economic data
    print("Loading economic data …")
    econ_df    = load_economic_data(ECONOMIC_PATH)
    borough_econ = build_borough_economic_summary(econ_df)

    merged = combined.merge(
        borough_econ, left_on="borough", right_on="Borough", how="left"
    )
    unmatched = merged[merged["Borough"].isna()]["borough"].unique()
    if len(unmatched):
        print(f"  ⚠ No economic data for boroughs: {unmatched}")
    merged.to_csv(OUT_MERGED, index=False)
    print(f"  → {OUT_MERGED.name}: {len(merged)} rows")

    # 4. Borough disruption summary (Power BI KPI table)
    summary = merged.groupby("borough", as_index=False).agg(
        lines_reported          = ("name",            "nunique"),
        disrupted_lines         = ("is_disrupted",    "sum"),
        average_severity        = ("statusSeverity",  "mean"),
        total_sales_m           = ("total_sales_m",   "first"),
        total_gva_m             = ("total_gva_m",     "first"),
        total_employees         = ("total_employees", "first"),
        total_companies         = ("total_companies", "first"),
        forecast_sales_2024_25  = ("forecast_sales_2024_25", "first"),
        forecast_sales_2025_26  = ("forecast_sales_2025_26", "first"),
        forecast_sales_2026_27  = ("forecast_sales_2026_27", "first"),
        forecast_sales_2027_28  = ("forecast_sales_2027_28", "first"),
        forecast_sales_2028_29  = ("forecast_sales_2028_29", "first"),
    )
    summary["disruption_rate_pct"] = (
        summary["disrupted_lines"] / summary["lines_reported"] * 100
    ).round(1)
    summary.to_csv(OUT_SUMMARY, index=False)
    print(f"  → {OUT_SUMMARY.name}: {len(summary)} boroughs")

    print("\n✅ Data integration complete.")
    print("Power BI input files:")
    for f in [OUT_COMBINED, OUT_DISRUPTION, OUT_MERGED, OUT_SUMMARY]:
        print(f"  {f}")


if __name__ == "__main__":
    main()
