# Power BI Dashboard Guide  
## London Transport Reliability & Economic Impact

---

## 1. Files to Import into Power BI

Run the updated Python scripts first, then import these 7 CSV files:

| File | Use in Power BI |
|---|---|
| `all_lines_combined.csv` | Master fact table – every line, every mode, every date |
| `disruption_enriched.csv` | Disruption fact table – only disrupted rows with root cause |
| `merged_transport_economic.csv` | Line-level fact table joined to economic data |
| `borough_disruption_summary.csv` | Borough KPI dimension table |
| `disruption_cause_summary.csv` | Cause breakdown dimension |
| `mode_disruption_summary.csv` | Mode-level summary |
| `forecast_disruption_risk.csv` | Risk scores + economic forecast by borough |

---

## 2. Data Model (Star Schema)

```
                   ┌─────────────────────────┐
                   │  borough_disruption_     │
                   │  summary (DIM)           │
                   │  borough [PK]            │
                   └──────────┬──────────────┘
                              │ borough
         ┌────────────────────┼─────────────────────┐
         │                    │                      │
┌────────▼──────────┐ ┌───────▼──────────┐ ┌────────▼──────────┐
│ all_lines_combined│ │disruption_enriched│ │forecast_disruption│
│ (FACT)            │ │(FACT)             │ │_risk (DIM)        │
│ name, modeName    │ │name, disruption_  │ │composite_risk_    │
│ statusSeverity    │ │cause, affected_   │ │score, risk_band,  │
│ borough           │ │section, reason    │ │estimated_gva...   │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

**Relationships to create:**
- `all_lines_combined[borough]` → `borough_disruption_summary[borough]` (Many:1)
- `disruption_enriched[borough]` → `borough_disruption_summary[borough]` (Many:1)
- `forecast_disruption_risk[borough]` → `borough_disruption_summary[borough]` (1:1)
- `disruption_enriched[name]` → `all_lines_combined[name]` (Many:Many cross-filter)

---

## 3. DAX Measures to Create

Paste these into **New Measure** in Power BI Desktop:

```dax
-- % of lines currently disrupted
Disruption Rate % = 
DIVIDE(
    COUNTROWS(FILTER('all_lines_combined', 'all_lines_combined'[is_disrupted] = TRUE())),
    COUNTROWS('all_lines_combined'),
    0
) * 100

-- Average severity (lower = worse)
Avg Severity = AVERAGE('all_lines_combined'[statusSeverity])

-- GVA at risk (sum across selected boroughs)
Total GVA at Risk £m = SUM('forecast_disruption_risk'[estimated_gva_at_risk_m])

-- Disruption count
Total Disruptions = COUNTROWS('disruption_enriched')

-- Most common cause
Top Cause = 
TOPN(1, VALUES('disruption_enriched'[disruption_cause]),
     CALCULATE(COUNTROWS('disruption_enriched')), DESC)

-- Severity band label
Severity Band = 
SWITCH(TRUE(),
    [Avg Severity] >= 9,  "✅ Good Service",
    [Avg Severity] >= 7,  "⚠️ Minor Issues",
    [Avg Severity] >= 5,  "🟠 Moderate",
                          "🔴 Severe"
)
```

---

## 4. Recommended Visuals & Pages

### Page 1 – Network Overview (Overview KPIs)
| Visual | Fields |
|---|---|
| Card | Disruption Rate % (measure) |
| Card | Total Disruptions |
| Card | Avg Severity |
| Card | Total GVA at Risk £m |
| Stacked Bar Chart | modeName on X, count of lines on Y, colour by severity_label |
| Donut Chart | severity_label (from all_lines_combined) |
| Table | name, modeName, severity_label, borough, reason |

### Page 2 – Disruption Deep Dive
| Visual | Fields |
|---|---|
| Bar Chart (horizontal) | disruption_cause on Y, incidents on X (from cause summary) |
| Matrix | borough rows × disruption_cause columns → count of incidents |
| Bar Chart | modeName on X, disruption_rate_pct on Y (from mode_disruption_summary) |
| Card | Top Cause (DAX measure) |
| Table | All columns from disruption_enriched.csv, filtered by is_disrupted = True |
| Slicer | severity_label (filter page to specific severities) |

### Page 3 – Economic Impact
| Visual | Fields |
|---|---|
| Scatter Chart | X = total_gva_m, Y = average_severity, Size = total_employees, colour = disruption_rate_pct |
| Scatter Chart | X = total_employees, Y = disruption_rate_pct, colour = total_gva_m |
| Bar Chart | borough on X, estimated_gva_at_risk_m on Y, colour = risk_band |
| Table | borough, total_gva_m, total_employees, disruption_rate_pct, average_severity |

### Page 4 – Risk & Forecast
| Visual | Fields |
|---|---|
| Bar Chart | borough on X, composite_risk_score on Y, colour = risk_band |
| Stacked Bar | borough rows, forecast_sales columns (2024/25–2028/29) – shows growth trend |
| Line Chart | year (unpivoted) on X, forecast_sales_m on Y, colour = borough |
| Gauge | composite_risk_score for selected borough (filtered by slicer) |
| Matrix | borough × risk_band counts |
| Slicer | risk_band (Critical / High / Medium / Low / Very Low) |

---

## 5. Suggested Slicers (add to every page)

- **Borough** (from `borough_disruption_summary[borough]`)
- **Transport Mode** (`all_lines_combined[modeName]`)
- **Severity Label** (`all_lines_combined[severity_label]`)
- **Disruption Cause** (`disruption_enriched[disruption_cause]`)
- **Risk Band** (`forecast_disruption_risk[risk_band]`)

---

## 6. Colour Theme Recommendation

| Status | Hex |
|---|---|
| Good Service | `#27AE60` |
| Minor Delays | `#F39C12` |
| Severe Delays | `#E74C3C` |
| Suspended | `#7F0000` |
| Risk: Critical | `#7F0000` |
| Risk: High | `#E74C3C` |
| Risk: Medium | `#F39C12` |
| Risk: Low | `#27AE60` |

Import as a Power BI theme JSON or apply manually in Format pane.

---

## 7. Refresh & Automation

To keep the dashboard live:

1. Schedule `data_integration.py` and `correlation_analysis.py` as a cron job / Windows Task.
2. Point the TfL API fetches in `scripts/app.py` to live endpoints (they are already there – just call them on a schedule).
3. In Power BI Desktop: **Transform Data → Data Source Settings → Change Source** → point to the output folder.
4. For cloud refresh: publish to Power BI Service → Gateway → scheduled refresh.

---

## 8. Future Enhancements

- **Geospatial map**: Add borough boundary GeoJSON from GLA → use ArcGIS or Shape Map visual to colour boroughs by risk score.
- **Time-series**: Collect snapshots daily → add `date` as an axis to show disruption trends over weeks/months.
- **Predictive alerts**: Use the `composite_risk_score` threshold (e.g., > 0.5) to trigger Power BI alerts or email notifications.
- **Strike history overlay**: Add a date dimension table with strike dates → overlay onto time-series charts as reference lines.
