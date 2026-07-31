"""
dashboard.py  –  London Transport Reliability & Economic Impact
Streamlit dashboard.  Run:  streamlit run dashboard.py
"""
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROOT     = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

st.set_page_config(page_title="London Transport Dashboard", layout="wide")
st.title("🚇 London Transport Reliability & Economic Impact")


# ── Load data ──────────────────────────────────────────────────────────────────
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
    }
    for key, fname in files.items():
        p = DATA_DIR / fname
        if p.exists():
            dfs[key] = pd.read_csv(p)
        else:
            st.warning(f"Missing: {fname}  – run scripts/data_integration.py first")
            dfs[key] = pd.DataFrame()
    return dfs


data = load_data()
combined   = data["combined"]
disruption = data["disruption"]
summary    = data["summary"]
cause_df   = data["cause"]
mode_df    = data["mode"]
forecast   = data["forecast"]

# ── Sidebar filters ────────────────────────────────────────────────────────────
st.sidebar.header("Filters")
boroughs = sorted(summary["borough"].dropna().unique()) if not summary.empty else []
sel_boroughs = st.sidebar.multiselect("Borough(s)", boroughs, default=boroughs)

modes = sorted(combined["modeName"].dropna().unique()) if not combined.empty else []
sel_modes = st.sidebar.multiselect("Transport Mode(s)", modes, default=modes)

filt_summary  = summary[summary["borough"].isin(sel_boroughs)]
filt_combined = combined[
    combined["borough"].isin(sel_boroughs) & combined["modeName"].isin(sel_modes)
]
filt_disruption = disruption[disruption["borough"].isin(sel_boroughs)]

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

    st.subheader("Disruption Detail (service_disruption.csv)")
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

# ── Tab 3 : Economic Impact ────────────────────────────────────────────────────
with tab3:
    col_e, col_f = st.columns(2)

    with col_e:
        st.subheader("GVA vs Disruption Severity")
        if not filt_summary.empty:
            fig6 = px.scatter(
                filt_summary, x="total_gva_m", y="average_severity",
                text="borough", size="total_employees",
                color="disruption_rate_pct", color_continuous_scale="RdYlGn_r",
                labels={"total_gva_m": "Borough GVA (£m)",
                        "average_severity": "Avg Severity (10=Good)",
                        "disruption_rate_pct": "Disruption %"},
                title="GVA vs Disruption (bubble = employment)",
            )
            fig6.update_traces(textposition="top center")
            st.plotly_chart(fig6, use_container_width=True)

    with col_f:
        st.subheader("Employment vs Disruption Rate")
        if not filt_summary.empty and "disruption_rate_pct" in filt_summary.columns:
            fig7 = px.scatter(
                filt_summary, x="total_employees", y="disruption_rate_pct",
                text="borough", color="total_gva_m",
                color_continuous_scale="Blues",
                labels={"total_employees": "Total Employees",
                        "disruption_rate_pct": "Disruption Rate (%)"},
                title="Employment vs Disruption Rate",
            )
            fig7.update_traces(textposition="top center")
            st.plotly_chart(fig7, use_container_width=True)

    st.subheader("Borough Economic Summary")
    if not filt_summary.empty:
        econ_cols = ["borough", "lines_reported", "disrupted_lines", "disruption_rate_pct",
                     "average_severity", "total_gva_m", "total_sales_m",
                     "total_employees", "total_companies"]
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
            st.subheader("Economic Forecast: Sales Growth")
            forecast_cols = ["borough",
                             "forecast_sales_2024_25", "forecast_sales_2025_26",
                             "forecast_sales_2026_27", "forecast_sales_2027_28",
                             "forecast_sales_2028_29"]
            avail = [c for c in forecast_cols if c in filt_forecast.columns]
            if len(avail) > 1:
                melted = filt_forecast[avail].melt(
                    id_vars="borough", var_name="year", value_name="forecast_sales_m"
                )
                melted["year"] = melted["year"].str.replace("forecast_sales_", "").str.replace("_", "/")
                fig10 = px.line(
                    melted, x="year", y="forecast_sales_m", color="borough",
                    markers=True, title="Forecast Sales by Borough (£m)",
                    labels={"forecast_sales_m": "Forecast Sales (£m)", "year": "Year"},
                )
                st.plotly_chart(fig10, use_container_width=True)

        st.subheader("Full Risk Table")
        risk_display_cols = ["borough", "composite_risk_score", "risk_band",
                             "disruption_rate_pct", "average_severity",
                             "estimated_gva_at_risk_m", "total_gva_m"]
        avail = [c for c in risk_display_cols if c in filt_forecast.columns]
        st.dataframe(filt_forecast[avail].sort_values("composite_risk_score", ascending=False),
                     use_container_width=True)
    else:
        st.info("Run scripts/correlation_analysis.py to generate forecast data.")

st.sidebar.divider()
st.sidebar.caption("Data: TfL API + GLA LCEGS 2023/24  |  Refresh: run data_integration.py")
