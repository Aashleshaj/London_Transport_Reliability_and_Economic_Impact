# 🚇 London Transport Reliability & Economic Impact

> **Does transport unreliability hit outer London harder than the centre — and what does it cost the economy?**
>
> This project collects live TfL service status data across all modes (Tube, Overground, DLR, Elizabeth line), classifies disruptions by root cause, merges them with borough-level economic data, and surfaces actionable insight through a Streamlit dashboard and a Power BI report.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Research Questions](#2-research-questions)
3. [Data Sources](#3-data-sources)
4. [Project Structure](#4-project-structure)
5. [Data Files Explained](#5-data-files-explained)
6. [Code Changes & What Was Added](#6-code-changes--what-was-added)
7. [How to Run](#7-how-to-run)
8. [Key Findings & Outcomes](#8-key-findings--outcomes)
9. [Power BI Dashboard Guide](#9-power-bi-dashboard-guide)
10. [Future Enhancements](#10-future-enhancements)
11. [Official Data Sources](#11-official-data-sources)

---

## 1. Project Overview

Public transport delays, strikes, and infrastructure failures do not affect all areas equally. This project investigates whether transport unreliability disproportionately impacts commuters in outer boroughs (such as Brent or Croydon) compared to central London, and correlates those disruptions with local economic data (GVA, employment, sales, and forecast revenue).

The pipeline goes from raw TfL JSON → cleaned CSVs → statistical analysis → a Streamlit dashboard and Power BI–ready flat files.

---

## 2. Research Questions

- Which London transport lines and modes experience the most disruptions?
- What are the most common root causes (signal failures, fire alerts, faulty trains, etc.)?
- Does disruption severity correlate with a borough's economic output (GVA, employment)?
- Which boroughs face the greatest economic risk from transport unreliability?
- What does the economic forecast look like for affected boroughs over the next five years?

---

## 3. Data Sources

### TfL API (live snapshots — manual download)

| File | TfL Endpoint | Coverage |
|---|---|---|
| `Status.json` | `https://api.tfl.gov.uk/Line/Mode/overground/Status` | Overground only |
| `tube_status.json` | `https://api.tfl.gov.uk/Line/Mode/tube/Status` | Tube only |
| `Status_all.json` | `https://api.tfl.gov.uk/Line/Mode/tube,overground,elizabeth-line,dlr/Status` | All modes |
| `service_disturption.json` | `https://api.tfl.gov.uk/Line/Mode/tube,overground/Status?detail=true` | Disruptions with full reason text |
| `economic_data.csv` | `https://data.london.gov.uk/dataset/low-carbon-environmental-goods-and-services-sector-lcegs-snapsho-2rjz1` | Economic_data created from kMatrix_LCEGS_GLA_2023_24_Datasets |

TfL API home: https://api.tfl.gov.uk  
TfL Open Data portal: https://tfl.gov.uk/info-for/open-data-users

### Economic Data (GLA LCEGS 2023/24)

Borough-level economic data sourced from the GLA Low Carbon & Environmental Goods and Services dataset:  
https://data.london.gov.uk/dataset/low-carbon-environmental-goods-and-services-sector-lcegs-snapsho-2rjz1

Fields used: Sales £m, GVA £m, Export Total £m, Total Imports £m, Number of Companies, Total Employees, and 5-year sales forecasts (2024/25 → 2028/29).

### Supporting / Reference Sources

| Category | Source | URL |
|---|---|---|
| Census travel data | ONS Census 2021 | https://www.ons.gov.uk/datasets/TS061 |
| Borough boundaries | GLA / London Datastore | https://data.london.gov.uk |
| Delay attribution | Office of Rail and Road | https://dataportal.orr.gov.uk |
| Passenger surveys | Transport Focus | https://www.transportfocus.org.uk |
| Strike history | Wikipedia / RMT | https://en.wikipedia.org/wiki/London_Underground_strikes |
| Labour market data | ONS Nomis | https://www.nomisweb.co.uk |

---

## 4. Project Structure

```
London_Transport_Reliability_and_Economic_Impact/
│
├── dashboard.py                    # Streamlit dashboard (4 tabs)
│
├── scripts/
│   ├── app.py                      # JSON → CSV converter
│   ├── data_integration.py         # ★ Enriched – merges all transport + economic sources
│   └── correlation_analysis.py     # ★ Enriched – root-cause analysis, risk scoring, forecasting
│
└── data/
    │
    ├── ── RAW INPUTS ──────────────────────────────────────────────
    ├── Status.csv                  # Tube-only snapshot (11 lines)
    ├── Status_all.csv              # All modes: tube + DLR + Elizabeth + Overground (19 lines)
    ├── service_disturption.csv     # Disrupted lines only, with full reason text
    ├── tube_status.csv             # Tube snapshot (same structure as Status.csv)
    ├── economic_data.csv           # Borough-level GVA, sales, employment, 5-yr forecast
    │
    ├── ── GENERATED OUTPUTS (Power BI inputs) ──────────────────────
    ├── all_lines_combined.csv      # ★ NEW – all modes, unified
    ├── disruption_enriched.csv     # ★ NEW – disrupted rows + root cause + affected section
    ├── merged_transport_economic.csv   # Lines joined to economic borough data
    ├── borough_disruption_summary.csv  # Borough KPI table (disruption rate, GVA, employees)
    ├── disruption_cause_summary.csv    # ★ NEW – cause breakdown (incidents, severity)
    ├── mode_disruption_summary.csv     # ★ NEW – per-mode disruption rate
    ├── forecast_disruption_risk.csv    # ★ NEW – risk score, risk band, GVA at risk per borough
    └── correlation_report.txt          # ★ NEW – Pearson correlation results
```

---

## 5. Data Files Explained

### Input CSVs

| File | Rows | Key Columns | Notes |
|---|---|---|---|
| `Status.csv` | 11 | name, modeName, statusSeverity, reason | Tube only |
| `Status_all.csv` | 19 | name, modeName, statusSeverity, reason | All modes including DLR, Elizabeth, Overground |
| `service_disturption.csv` | 17 | name, statusSeverity, reason, disruptionDescription | Contains detailed reason text — used for root-cause classification |
| `economic_data.csv` | ~2,000 | Borough, GVA £m, Sales £m, Employees, Forecasts | GLA LCEGS sector-level data, aggregated to borough level |

### Generated Output CSVs (Power BI inputs)

| File | Rows | Purpose |
|---|---|---|
| `all_lines_combined.csv` | 36 | Master fact table — every line from every source, deduplicated |
| `disruption_enriched.csv` | 7 | Only disrupted rows; adds `disruption_cause` and `affected_section` |
| `merged_transport_economic.csv` | 36 | Lines joined to borough economic data |
| `borough_disruption_summary.csv` | 9 | Borough KPIs: disruption rate, avg severity, GVA, employees |
| `disruption_cause_summary.csv` | 4 | Cause breakdown: Fire Alert, Signal Failure, Faulty Train, Customer Incident |
| `mode_disruption_summary.csv` | 4 | Disruption rate per mode: tube, overground, DLR, Elizabeth line |
| `forecast_disruption_risk.csv` | 9 | Composite risk score (0–1), risk band, estimated GVA at risk (£m) |

---

## 6. Code 

### `scripts/data_integration.py`

- Loads all transport CSVs (`Status.csv`, `Status_all.csv`, `service_disturption.csv`) and unifies them into a single deduplicated fact table.
- Expanded `LINE_TO_BOROUGH` mapping from 11 entries to 19, covering all Overground strands (e.g. Liberty → Havering, Mildmay → Hackney, Windrush → Lambeth), DLR → Tower Hamlets, and Elizabeth line → Westminster.
- Added `disruption_cause` column via a regex classifier that extracts root cause from reason text: Fire Alert, Signal Failure, Faulty Train, Customer Incident, Points Failure, Flooding, Strike, and more.
- Added `affected_section` column extracting "between X and Y" from reason text.
- Added `is_disrupted` boolean and `severity_label` human-readable column.
- Borough summary now includes `disruption_rate_pct` (disrupted lines ÷ total lines × 100).
- Outputs 4 Power BI–ready files (was 2).

**New output files produced:**
- `all_lines_combined.csv` — 36 rows across 19 lines and 4 modes
- `disruption_enriched.csv` — 7 disrupted service records with cause and section

### `scripts/correlation_analysis.py` 

- Generates `disruption_cause_summary.csv` — cause frequency, lines affected, and average severity per cause.
- Generates `mode_disruption_summary.csv` — disruption rate by transport mode.
- Generates `forecast_disruption_risk.csv` with a **composite risk score** (0–1) for each borough, combining severity risk and disruption rate:
  - `severity_risk = (10 − avg_severity) / 9`
  - `rate_risk = disruption_rate_pct / 100`
  - `composite_risk_score = 0.6 × severity_risk + 0.4 × rate_risk`
- Adds a `risk_band` label (Very Low / Low / Medium / High / Critical).
- Adds `estimated_gva_at_risk_m` — modelled as `GVA × composite_risk × 2%` daily sensitivity.
- Runs Pearson correlations for 5 metric pairs and writes a plain-text `correlation_report.txt`.

### `dashboard.py` 

| Tab | Content |
|---|---|
| 🚦 Live Status | Status by mode, severity donut, full line table |
| ⚠️ Disruption Analysis | Cause bar chart, mode disruption rate, disruption detail table |
| 💷 Economic Impact | GVA vs severity scatter, employment vs disruption rate scatter |
| 🔮 Forecast & Risk | Composite risk bar, GVA at risk bar, 5-year forecast sales line chart |

---

## 7. How to Run

### Install dependencies

```bash
pip install pandas scipy streamlit plotly
```

### Step 1 — Convert JSON to CSV (if you have fresh API data)

```bash
cd scripts
python app.py
```

This converts all `.json` files in `data/` to `.csv` format.

### Step 2 — Run data integration

```bash
python scripts/data_integration.py
```

Produces: `all_lines_combined.csv`, `disruption_enriched.csv`, `merged_transport_economic.csv`, `borough_disruption_summary.csv`

### Step 3 — Run correlation analysis & risk scoring

```bash
python scripts/correlation_analysis.py
```

Produces: `disruption_cause_summary.csv`, `mode_disruption_summary.csv`, `forecast_disruption_risk.csv`, `correlation_report.txt`

### Step 4 — Launch Streamlit dashboard

```bash
streamlit run dashboard.py
```

### Step 5 — Open in Power BI

Import all 7 output CSVs into Power BI Desktop. See Section 9 for the full setup guide.

---

## 8. Key Findings & Outcomes

All findings below are based on the snapshot data collected from the TfL API.

### Network Disruption Summary

| Mode | Total Lines | Disrupted | Disruption Rate |
|---|---|---|---|
| Tube | 11 | 9 | **81.8%** |
| Overground | 6 | 2 | **33.3%** |
| Elizabeth line | 1 | 1 | **100.0%** |
| DLR | 1 | 0 | **0.0%** |

### Disruption Root Causes

| Cause | Incidents | Lines Affected | Avg Severity | Category |
|---|---|---|---|---|
| Fire Alert | 3 | 3 | 4.7 | 🔴 Severe |
| Signal Failure | 2 | 2 | 3.0 | 🔴 Severe |
| Customer Incident | 1 | 1 | 6.0 | 🔴 Severe |
| Faulty Train | 1 | 1 | 9.0 | 🟡 Minor |

Fire alerts and signal failures account for the most severe disruptions. Signal failures produce the lowest severity scores (3.0 average — indicating near-suspension).

### Borough Risk Scores

| Borough | Risk Score | Risk Band | Disruption Rate | GVA at Risk (£m) | Total GVA (£m) |
|---|---|---|---|---|---|
| Hackney | 0.633 | 🔴 High | 100% | £5.31m | £419.6m |
| Camden | 0.533 | 🟠 Medium | 100% | £10.57m | £991.2m |
| Lambeth | 0.533 | 🟠 Medium | 100% | £4.12m | £386.8m |
| Westminster | 0.457 | 🟠 Medium | 80% | £12.01m | £1,313.9m |
| Islington | 0.433 | 🟠 Medium | 100% | £5.51m | £635.8m |
| Brent | 0.000 | ✅ Very Low | 0% | £0.00m | £252.6m |
| Tower Hamlets | 0.000 | ✅ Very Low | 0% | £0.00m | £287.2m |

Westminster carries the highest absolute GVA at risk (£12.01m) due to its large economic base. Hackney has the highest relative risk score (0.633) because the Mildmay line experienced Part Suspension during the snapshot.

### Pearson Correlations (Borough-level)

| Pair | r | p-value | Interpretation |
|---|---|---|---|
| Avg Severity vs GVA | −0.508 | 0.163 | Moderate negative — higher-GVA boroughs tend to have worse disruptions |
| Avg Severity vs Employment | −0.469 | 0.203 | Moderate negative — similar pattern |
| Avg Severity vs Sales | −0.518 | 0.153 | Moderate negative |
| Disruption Rate % vs GVA | +0.634 | 0.066 | Strongest signal — higher GVA boroughs see more lines disrupted |
| Disruption Rate % vs Employment | +0.544 | 0.130 | Moderate positive |

> Note: p-values are above 0.05 because the sample covers only 9 boroughs. These correlations will become statistically significant as more snapshot dates are collected over time.

### Economic Forecast (5-Year Sales, £m)

Top boroughs by forecast sales growth 2024/25 → 2028/29:

| Borough | 2024/25 | 2025/26 | 2026/27 | 2027/28 | 2028/29 |
|---|---|---|---|---|---|
| Westminster | £152m | £165m | £180m | £198m | £220m |
| Camden | £122m | £133m | £145m | £160m | £177m |
| Islington | £80m | £87m | £95m | £104m | £115m |

All boroughs show consistent upward sales forecasts over the 5-year window, making the cost of transport disruption relatively more impactful as economic stakes rise.

---

## 9. Power BI Dashboard Guide

### Files to Import

Import all 7 output CSVs from the `data/` folder:

1. `all_lines_combined.csv` — master fact table
2. `disruption_enriched.csv` — disruption fact table
3. `merged_transport_economic.csv` — line-level economic merge
4. `borough_disruption_summary.csv` — borough KPI dimension
5. `disruption_cause_summary.csv` — cause dimension
6. `mode_disruption_summary.csv` — mode dimension
7. `forecast_disruption_risk.csv` — risk and forecast dimension

### Relationships (star schema)

- `all_lines_combined[borough]` → `borough_disruption_summary[borough]` (Many:1)
- `disruption_enriched[borough]` → `borough_disruption_summary[borough]` (Many:1)
- `forecast_disruption_risk[borough]` → `borough_disruption_summary[borough]` (1:1)

### Key DAX Measures

```dax
Disruption Rate % =
DIVIDE(
    COUNTROWS(FILTER('all_lines_combined', 'all_lines_combined'[is_disrupted] = TRUE())),
    COUNTROWS('all_lines_combined'), 0
) * 100

Total GVA at Risk £m = SUM('forecast_disruption_risk'[estimated_gva_at_risk_m])

Avg Severity = AVERAGE('all_lines_combined'[statusSeverity])

Total Disruptions = COUNTROWS('disruption_enriched')
```

### Recommended Pages

| Page | Key Visuals |
|---|---|
| Network Overview | KPI cards, stacked bar by mode/status, severity donut, full line table |
| Disruption Analysis | Cause bar chart, mode disruption rate, disruption detail table, borough disruption rate bar |
| Economic Impact | GVA vs severity scatter, employment vs disruption scatter, borough economic table |
| Forecast & Risk | Risk score bar by borough, GVA at risk bar, 5-year forecast line chart, risk table |

### Recommended Slicers

Add to every page: Borough, Transport Mode, Severity Label, Disruption Cause, Risk Band.

### Colour Convention

| Status / Band | Hex |
|---|---|
| Good Service / Very Low | `#27AE60` |
| Minor Delays / Low | `#2ECC71` |
| Moderate / Medium | `#F39C12` |
| Severe Delays / High | `#E74C3C` |
| Suspended / Critical | `#7F0000` |

---

## 10. Future Enhancements

| Enhancement | Description |
|---|---|
| Time-series collection | Schedule `app.py` to call the TfL API every hour. Add `date` as an axis to track disruption trends over weeks and months. |
| Geospatial map | Add GLA borough boundary GeoJSON → use Power BI Shape Map or ArcGIS to colour boroughs by risk score. |
| Strike overlay | Add a date dimension table with historical strike dates. Overlay on time-series charts as reference lines. |
| Real-time alerts | Trigger Power BI alerts or email notifications when `composite_risk_score` exceeds a threshold (e.g. 0.6). |
| Outer-borough expansion | Expand `LINE_TO_BOROUGH` to secondary boroughs served by each line (e.g. Jubilee → Southwark, Greenwich). |
| Machine learning | Train a classification model on historical disruption patterns to predict next-day risk by line. |
| Real economic data | Replace GLA LCEGS sample with ONS borough income estimates or GLA household income data for richer correlation. |

---

## 11. Official Data Sources

### TfL API

| Resource | URL |
|---|---|
| TfL API home | https://api.tfl.gov.uk |
| TfL Open Data portal | https://tfl.gov.uk/info-for/open-data-users |
| TfL API documentation | https://api.tfl.gov.uk/swagger/ui/index.html |
| TfL performance reports | https://tfl.gov.uk/corporate/publications-and-reports/underground-services-performance |

### ONS / Census

| Resource | URL |
|---|---|
| Census 2021 custom data | https://create.census.gov.uk/query |
| TS058 distance to work | https://www.ons.gov.uk/datasets/TS058/editions/2021/versions/3 |
| TS061 method of travel | https://www.ons.gov.uk/datasets/TS061/editions/2021/versions/3 |
| National Travel Survey | https://www.gov.uk/government/collections/national-travel-survey-statistics |

### London Data

| Resource | URL |
|---|---|
| London Datastore (GLA) | https://data.london.gov.uk |
| Borough boundary files | https://data.london.gov.uk/dataset/statistical-gis-boundary-files-london |
| Borough income estimates | https://data.london.gov.uk/dataset/household-income-estimates-small-areas |
| GLA LCEGS economic data | https://data.london.gov.uk/dataset/low-carbon-environmental-goods-and-services-sector-lcegs-snapsho-2rjz1 |
| LTDS travel report | https://tfl.gov.uk/corporate/publications-and-reports/travel-in-london-reports |

### Rail & Disruption

| Resource | URL |
|---|---|
| ORR data portal | https://dataportal.orr.gov.uk |
| Network Rail open data | https://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/open-data-feeds |
| Delay attribution data | https://dataportal.orr.gov.uk/statistics/performance/delay-attribution |

### Passenger & Impact

| Resource | URL |
|---|---|
| Transport Focus surveys | https://www.transportfocus.org.uk/research-publications |
| London TravelWatch | https://www.londontravelwatch.org.uk/resources/publications |
| Trust for London | https://trustforlondon.org.uk/data |
| ONS Nomis labour data | https://www.nomisweb.co.uk |

### Strike History

| Resource | URL |
|---|---|
| London Underground strikes | https://en.wikipedia.org/wiki/London_Underground_strikes |
| RMT union announcements | https://www.rmt.org.uk/news |

---

*Built with Python · pandas · scipy · Streamlit · Plotly · Power BI*  
*Data: Transport for London API · GLA LCEGS 2023/24 · ONS Census 2021*
