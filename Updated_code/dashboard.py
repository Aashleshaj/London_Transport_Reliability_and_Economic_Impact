"""
dashboard.py  –  London Transport Reliability & Economic Impact
Streamlit dashboard.  Run:  streamlit run dashboard.py

CHANGED:
  - Added a "🔴 Live now" panel at the top of Tab 1 that calls the TfL API
    directly (cached 2 min) — every visitor sees genuinely current status,
    independent of how recently the GitHub Actions logger last ran.
  - Added a "Last batch refresh" caption showing when data/tfl_status_history.csv
    was last updated.
  - Added a disruption-rate trend chart (Tab 2) using borough_disruption_daily.csv,
    which becomes meaningful once the live logger has run for a few days.
"""
import os
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
import pandas as pd
import requests
import plotly.express as px

ROOT     = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

st.set_page_config(page_title="London Transport Dashboard", layout="wide")
st.title("🚇 London Transport Reliability & Economic Impact")


# ── Live API call (bypasses the batch pipeline entirely) ───────────────────────
@st.cache_data(ttl=120)  # re-poll TfL at most once every 2 minutes per visitor
def fetch_live_status():
    app_id = os.getenv("TFL_APP_ID")
    app_key = os.getenv("TFL_APP_KEY") or os.getenv("APP_KEY")
    params = {"detail": "true"}
    if app_id:
        params["app_id"] = app_id
    if app_key:
        params["app_key"] = app_key

    url = "https://api.tfl.gov.uk/Line/Mode/tube,dlr,overground,elizabeth-line/Status"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    for line in data:
        statuses = line.get("lineStatuses", [])
        status = statuses[0] if statuses else {}
        rows.append({
            "name": line.get("name"),
            "modeName": line.get("modeName"),
            "statusSeverity": status.get("statusSeverity"),
            "statusSeverityDescription": status.get("statusSeverityDescription"),
            "reason": status.get("reason", ""),
        })
    return pd.DataFrame(rows), datetime.now(timezone.utc)


# ── Load batch-pipeline data ────────────────────────────────────────────────────
@st.cache_data
def load_data():
    dfs = {}
    files = {
        "combined":   "all_lines_combined.csv",
        "disruption": "disruption_enriched.csv",
        "merged":     "merged_transport_economic.csv",
        "summary":    "borough_disruption_summary.csv",
        "cause":      "disruption_cause_summary.csv",
        "mode":       "mode_disruption_summary.csv",
        "forecast":   "forecast_disruption_risk.csv",
        "daily":      "borough_disruption_daily.csv",   # NEW – trend data
    }
    for key, fname in files.items():
        p = DATA_DIR / fname
        if p.exists():
            dfs[key] = pd.read_csv(p)
        else:
            st.warning(f"Missing: {fname}  – run scripts/live_status_logger.py, "
                       f"scripts/fetch_economic_data.py, then "
                       f"scripts/build_dashboard_data.py first")
            dfs[key] = pd.DataFrame()
    return dfs


data = load_data()
combined   = data["combined"]
disruption = data["disruption"]
summary    = data["summary"]
cause_df   = data["cause"]
mode_df    = data["mode"]
forecast   = data["forecast"]
daily_df   = data["daily"]

# ── Sidebar filters ────────────────────────────────────────────────────────────
st.sidebar.header("Filters")
boroughs = sorted(summary["borough"].dropna().unique()) if not summary.empty else []
sel_boroughs = st.sidebar.multiselect("Borough(s)", boroughs, default=boroughs)

modes = sorted(combined["modeName"].dropna().unique()) if not combined.empty else []
sel_modes = st.sidebar.multiselect("Transport Mode(s)", modes, default=modes)

filt_summary = summary[summary["borough"].isin(sel_boroughs)] if not summary.empty else pd.DataFrame()

filt_combined = combined[
    combined["borough"].isin(sel_boroughs) & combined["modeName"].isin(sel_modes)
] if not combined.empty else pd.DataFrame()

filt_disruption = disruption[disruption["borough"].isin(sel_boroughs)] if not disruption.empty else pd.DataFrame()

# Show when the batch pipeline (history log) was last refreshed
history_path = DATA_DIR / "tfl_status_history.csv"
if history_path.exists():
    last_batch = pd.read_csv(history_path, usecols=["timestamp"])["timestamp"].max()
    st.sidebar.caption(f"📦 Batch data last logged: {last_batch}")

# ── KPI row ────────────────────────────────────────────────────────────────────
st.header("📊 Network Overview")
k1, k2, k3, k4, k5 = st.columns(5)

total_lines     = filt_combined["name"].nunique() if not filt_combined.empty else 0
disrupted_lines = int(filt_combined["is_disrupted"].sum()) if not filt_combined.empty else 0
avg_severity    = filt_combined["statusSeverity"].mean() if not filt_combined.empty else 0
disrupted_boroughs = int((filt_summary["disrupted_lines"] > 0).sum()) if not filt_summary.empty else 0
gva_at_risk     = filt_summary["estimated_gva_at_risk_m"].sum() if "estimated_gva_at_risk_m" in filt_summary.columns else 0

k1.metric("Total Lines Monitored", total_lines)
k2.metric("Lines Disrupted", disrupted_lines,
          delta=f"{disrupted_lines/total_lines*100:.0f}% of network" if total_lines else "")
k3.metric("Avg Severity Score", f"{avg_severity:.1f} / 10")
k4.metric("Boroughs with Disruption", disrupted_boroughs)
k5.metric("Est. GVA at Risk (£m)", f"£{gva_at_risk:.1f}m")

st.divider()

# ── Tab layout ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🚦 Live Status", "⚠️ Disruption Analysis", "💷 Economic Impact", "🔮 Forecast & Risk"
])

# ── Tab 1 : Live Status ────────────────────────────────────────────────────────
with tab1:
    st.subheader("🔴 Live right now (direct from TfL, refreshes every 2 min)")
    try:
        live_df, fetched_at = fetch_live_status()
        st.caption(f"Fetched at {fetched_at:%Y-%m-%d %H:%M:%S} UTC")
        live_disrupted = live_df[live_df["statusSeverity"] != 10]
        if live_disrupted.empty:
            st.success("✅ Good service on all monitored lines right now.")
        else:
            st.dataframe(
                live_disrupted[["name", "modeName", "statusSeverityDescription", "reason"]],
                use_container_width=True,
            )
    except Exception as e:
        st.error(f"Couldn't reach the live TfL API right now: {e}")

    st.divider()
    st.subheader("Batch snapshot (from the last scheduled logger run)")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Line Status by Mode")
        if not filt_combined.empty:
            fig = px.bar(
                filt_combined.groupby(["modeName", "severity_label"], as_index=False)
                              .agg(count=("name", "count")),
                x="modeName", y="count", color="severity_label",
                title="Lines by Mode & Status",
                color_discrete_map={
                    "Good Service":   "#27ae60",
                    "Minor Delays":   "#f39c12",
                    "Severe Delays":  "#e74c3c",
                    "Part Suspended": "#c0392b",
                    "Suspended":      "#7f0000",
                    "Unknown":        "#bdc3c7",
                },
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Severity Distribution")
        if not filt_combined.empty:
            vc = filt_combined["severity_label"].value_counts().reset_index()
            vc.columns = ["Status", "Count"]
            fig2 = px.pie(vc, names="Status", values="Count",
                          title="Current Status Mix", hole=0.4)
            st.plotly_chart(fig2, use_container_width=True)

    st.subheader("All Lines – Current Status")
    if not filt_combined.empty:
        display_cols = ["name", "modeName", "statusSeverity", "severity_label",
                        "borough", "is_disrupted", "reason"]
        available = [c for c in display_cols if c in filt_combined.columns]
        styled = filt_combined[available].sort_values("statusSeverity")
        st.dataframe(styled, use_container_width=True)

# ── Tab 2 : Disruption Analysis ────────────────────────────────────────────────
with tab2:
    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("Disruption Causes")
        if not cause_df.empty:
            fig3 = px.bar(
                cause_df.sort_values("incidents", ascending=True),
                x="incidents", y="disruption_cause", orientation="h",
                color="avg_severity",
                color_continuous_scale="RdYlGn",
                title="Incidents by Root Cause",
                labels={"incidents": "# Incidents", "disruption_cause": "Cause"},
            )
            st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        st.subheader("Disruption Rate by Mode")
        if not mode_df.empty:
            fig4 = px.bar(
                mode_df, x="modeName", y="disruption_rate_pct",
                color="avg_severity", color_continuous_scale="RdYlGn_r",
                title="% Lines Disrupted per Mode",
                labels={"disruption_rate_pct": "Disruption Rate (%)", "modeName": "Mode"},
            )
            st.plotly_chart(fig4, use_container_width=True)

    st.subheader("Disruption Detail (latest batch snapshot)")
    if not filt_disruption.empty:
        cols = ["name", "modeName", "severity_label", "disruption_cause",
                "affected_section", "reason", "borough"]
        avail = [c for c in cols if c in filt_disruption.columns]
        st.dataframe(filt_disruption[avail], use_container_width=True)
    else:
        st.info("No disruptions for selected filters.")

    st.subheader("Severity by Borough (all modes)")
    if not filt_summary.empty and "disruption_rate_pct" in filt_summary.columns:
        fig5 = px.bar(
            filt_summary.sort_values("disruption_rate_pct", ascending=False),
            x="borough", y="disruption_rate_pct",
            title="Disruption Rate % by Borough",
            labels={"disruption_rate_pct": "Disruption Rate (%)", "borough": "Borough"},
            color="disruption_rate_pct", color_continuous_scale="Reds",
        )
        st.plotly_chart(fig5, use_container_width=True)

    # NEW – trend chart, becomes meaningful once the live logger has run a few days
    st.subheader("Disruption Rate Trend Over Time")
    if not daily_df.empty and daily_df["date"].nunique() > 1:
        filt_daily = daily_df[daily_df["borough"].isin(sel_boroughs)]
        fig_trend = px.line(
            filt_daily.sort_values("date"),
            x="date", y="disruption_rate_pct", color="borough", markers=True,
            title="Daily Disruption Rate % by Borough",
            labels={"disruption_rate_pct": "Disruption Rate (%)", "date": "Date"},
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Trend chart needs more than one day of logged history — "
                "this fills in automatically as the GitHub Actions logger runs over time.")

# ── Tab 3 : Economic Impact ────────────────────────────────────────────────────
with tab3:
    col_e, col_f = st.columns(2)

    with col_e:
        st.subheader("GVA vs Disruption Severity")
        if not filt_summary.empty:
            fig6 = px.scatter(
                filt_summary, x="total_gva_m", y="average_severity",
                text="borough", size="disrupted_lines",
                color="disruption_rate_pct", color_continuous_scale="RdYlGn_r",
                labels={"total_gva_m": "Borough GVA (£m)",
                        "average_severity": "Avg Severity (10=Good)",
                        "disruption_rate_pct": "Disruption %"},
                title="GVA vs Disruption (bubble = # disrupted lines)",
            )
            fig6.update_traces(textposition="top center")
            st.plotly_chart(fig6, use_container_width=True)

    with col_f:
        st.subheader("GVA vs Disruption Rate")
        if not filt_summary.empty and "disruption_rate_pct" in filt_summary.columns:
            fig7 = px.scatter(
                filt_summary, x="total_gva_m", y="disruption_rate_pct",
                text="borough", color="average_severity",
                color_continuous_scale="RdYlGn",
                labels={"total_gva_m": "Borough GVA (£m)",
                        "disruption_rate_pct": "Disruption Rate (%)"},
                title="GVA vs Disruption Rate",
            )
            fig7.update_traces(textposition="top center")
            st.plotly_chart(fig7, use_container_width=True)

    st.subheader("Borough Economic Summary")
    st.caption("GVA sourced live from ONS. Employment/sales/company-count figures "
               "aren't shown here — those came from a commercial dataset with no "
               "free live API equivalent.")
    if not filt_summary.empty:
        econ_cols = ["borough", "lines_reported", "disrupted_lines", "disruption_rate_pct",
                     "average_severity", "total_gva_m"]
        avail = [c for c in econ_cols if c in filt_summary.columns]
        st.dataframe(filt_summary[avail], use_container_width=True)

# ── Tab 4 : Forecast & Risk ────────────────────────────────────────────────────
with tab4:
    st.subheader("Borough Composite Risk Score")
    if not forecast.empty and "composite_risk_score" in forecast.columns:
        filt_forecast = forecast[forecast["borough"].isin(sel_boroughs)]

        fig8 = px.bar(
            filt_forecast.sort_values("composite_risk_score", ascending=False),
            x="borough", y="composite_risk_score",
            color="risk_band",
            color_discrete_map={
                "Critical":  "#7f0000",
                "High":      "#e74c3c",
                "Medium":    "#f39c12",
                "Low":       "#27ae60",
                "Very Low":  "#2ecc71",
            },
            title="Composite Disruption Risk Score by Borough",
            labels={"composite_risk_score": "Risk Score (0–1)", "borough": "Borough"},
        )
        st.plotly_chart(fig8, use_container_width=True)

        col_g, col_h = st.columns(2)
        with col_g:
            st.subheader("Estimated GVA at Risk (£m)")
            fig9 = px.bar(
                filt_forecast.sort_values("estimated_gva_at_risk_m", ascending=False),
                x="borough", y="estimated_gva_at_risk_m",
                color="risk_band",
                title="Estimated GVA at Risk per Borough",
                labels={"estimated_gva_at_risk_m": "GVA at Risk (£m)"},
            )
            st.plotly_chart(fig9, use_container_width=True)

        with col_h:
            st.subheader("Risk Score vs Borough GVA")
            if not daily_df.empty:
                fig10 = px.scatter(
                    filt_forecast, x="total_gva_m", y="composite_risk_score",
                    text="borough", color="risk_band",
                    color_discrete_map={
                        "Critical": "#7f0000", "High": "#e74c3c",
                        "Medium": "#f39c12", "Low": "#27ae60", "Very Low": "#2ecc71",
                    },
                    title="Composite Risk Score vs Borough GVA",
                    labels={"total_gva_m": "Borough GVA (£m)",
                            "composite_risk_score": "Risk Score (0–1)"},
                )
                fig10.update_traces(textposition="top center")
                st.plotly_chart(fig10, use_container_width=True)

        st.subheader("Full Risk Table")
        risk_display_cols = ["borough", "composite_risk_score", "risk_band",
                             "disruption_rate_pct", "average_severity",
                             "estimated_gva_at_risk_m", "total_gva_m"]
        avail = [c for c in risk_display_cols if c in filt_forecast.columns]
        st.dataframe(filt_forecast[avail].sort_values("composite_risk_score", ascending=False),
                     use_container_width=True)
    else:
        st.info("Run scripts/build_dashboard_data.py to generate risk/forecast data.")

st.sidebar.divider()
st.sidebar.caption("Data: TfL API (live) + ONS GVA by local authority (live)  |  "
                    "Live panel refreshes every 2 min · Batch data refreshes via GitHub Actions")