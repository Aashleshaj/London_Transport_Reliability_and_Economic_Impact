"""
correlation_analysis.py  –  Statistical analysis + simple trend forecasting
Reads the enriched files produced by data_integration.py and outputs:
  - disruption_cause_summary.csv   (cause breakdown – Power BI bar chart)
  - mode_disruption_summary.csv    (tube vs overground vs DLR – Power BI donut)
  - forecast_disruption_risk.csv   (borough risk score + economic forecast)
  - correlation_report.txt         (Pearson r results)
"""
from pathlib import Path
import pandas as pd
from scipy.stats import pearsonr

ROOT        = Path(__file__).resolve().parent.parent
DATA_DIR    = ROOT / "data"

MERGED_PATH    = DATA_DIR / "merged_transport_economic.csv"
DISRUPTION_PATH = DATA_DIR / "disruption_enriched.csv"
COMBINED_PATH  = DATA_DIR / "all_lines_combined.csv"
SUMMARY_PATH   = DATA_DIR / "borough_disruption_summary.csv"

OUT_CAUSE    = DATA_DIR / "disruption_cause_summary.csv"
OUT_MODE     = DATA_DIR / "mode_disruption_summary.csv"
OUT_FORECAST = DATA_DIR / "forecast_disruption_risk.csv"
OUT_REPORT   = DATA_DIR / "correlation_report.txt"


def pearson_safe(x: pd.Series, y: pd.Series):
    valid = pd.concat([x, y], axis=1).dropna()
    if len(valid) < 2:
        return None, None
    return pearsonr(valid.iloc[:, 0], valid.iloc[:, 1])


def main():
    merged    = pd.read_csv(MERGED_PATH)
    disrupt   = pd.read_csv(DISRUPTION_PATH)
    combined  = pd.read_csv(COMBINED_PATH)
    summary   = pd.read_csv(SUMMARY_PATH)

    report_lines = ["London Transport – Correlation & Disruption Analysis", "=" * 60, ""]

    # ── 1. Disruption cause breakdown ─────────────────────────────────────────
    cause_counts = (
        disrupt.groupby("disruption_cause", as_index=False)
        .agg(
            incidents          = ("name", "count"),
            lines_affected     = ("name", "nunique"),
            avg_severity       = ("statusSeverity", "mean"),
        )
        .sort_values("incidents", ascending=False)
    )
    cause_counts["severity_label"] = cause_counts["avg_severity"].apply(
        lambda s: "Severe" if s <= 6 else ("Moderate" if s <= 8 else "Minor")
    )
    cause_counts.to_csv(OUT_CAUSE, index=False)
    report_lines += ["Disruption Cause Breakdown:", cause_counts.to_string(index=False), ""]

    # ── 2. Mode-level disruption summary ──────────────────────────────────────
    mode_summary = (
        combined.groupby("modeName", as_index=False)
        .agg(
            total_lines      = ("name", "nunique"),
            disrupted_lines  = ("is_disrupted", "sum"),
            avg_severity     = ("statusSeverity", "mean"),
        )
    )
    mode_summary["disruption_rate_pct"] = (
        mode_summary["disrupted_lines"] / mode_summary["total_lines"] * 100
    ).round(1)
    mode_summary.to_csv(OUT_MODE, index=False)
    report_lines += ["Mode Disruption Summary:", mode_summary.to_string(index=False), ""]

    # ── 3. Pearson correlations ────────────────────────────────────────────────
    pairs = [
        ("average_severity", "total_gva_m",       "Severity vs Borough GVA"),
        ("average_severity", "total_employees",    "Severity vs Employment"),
        ("average_severity", "total_sales_m",      "Severity vs Sales"),
        ("disruption_rate_pct", "total_gva_m",     "Disruption Rate % vs GVA"),
        ("disruption_rate_pct", "total_employees", "Disruption Rate % vs Employment"),
    ]
    report_lines.append("Pearson Correlations:")
    for col_a, col_b, label in pairs:
        if col_a in summary.columns and col_b in summary.columns:
            r, p = pearson_safe(summary[col_a], summary[col_b])
            if r is not None:
                report_lines.append(f"  {label}: r={r:.3f}, p={p:.3f}")
    report_lines.append("")

    # ── 4. Borough disruption-risk + economic forecast ────────────────────────
    forecast = summary.copy()

    # Simple risk score: weighted mix of disruption rate and inverse severity
    # Higher disruption_rate + lower avg severity (more severe) → higher risk
    forecast["severity_risk"] = (10 - forecast["average_severity"]) / 9      # 0-1
    forecast["rate_risk"]     = forecast["disruption_rate_pct"] / 100        # 0-1
    forecast["composite_risk_score"] = (
        0.6 * forecast["severity_risk"] + 0.4 * forecast["rate_risk"]
    ).round(3)
    forecast["risk_band"] = pd.cut(
        forecast["composite_risk_score"],
        bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
        labels=["Very Low", "Low", "Medium", "High", "Critical"],
    )

    # Estimated economic exposure (GVA at risk if disruption worsens)
    # Simple model: GVA × composite_risk_score × 0.02 (assume 2% daily sensitivity)
    forecast["estimated_gva_at_risk_m"] = (
        forecast["total_gva_m"] * forecast["composite_risk_score"] * 0.02
    ).round(2)

    # Forecast sales columns already exist from economic data
    forecast.to_csv(OUT_FORECAST, index=False)
    report_lines += [
        "Borough Risk Scores:",
        forecast[["borough", "composite_risk_score", "risk_band",
                   "estimated_gva_at_risk_m"]].to_string(index=False),
        "",
    ]

    # ── Write report ──────────────────────────────────────────────────────────
    report_text = "\n".join(report_lines)
    OUT_REPORT.write_text(report_text)
    print(report_text)

    print("\n✅ Analysis complete. Output files:")
    for f in [OUT_CAUSE, OUT_MODE, OUT_FORECAST, OUT_REPORT]:
        print(f"  {f}")


if __name__ == "__main__":
    main()
