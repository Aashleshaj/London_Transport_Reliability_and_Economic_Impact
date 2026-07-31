# London Transport Reliability & Economic Impact — Power BI Setup Guide

This walks through everything end to end: confirming the live GitHub pipeline is
actually running, then building the Power BI report on top of it, file by file.

---

## Part 1 — Confirm the live pipeline is working

Do this before touching Power BI. Power BI will just show empty/stale visuals
if the repo isn't actually being updated yet.

### 1.1 Repo structure check
Your repo should now look like this:

```
scripts/
  live_status_logger.py
  fetch_economic_data.py
  build_dashboard_data.py
data/
  (empty until first Action run — this is expected)
.github/workflows/
  tfl_live.yml
  economic_data.yml
dashboard.py
```

Confirm the old files are gone: `app.py`, `data_integration.py`,
`correlation_analysis.py`, `economic_data.csv`, `kMatrix_LCEGS_GLA_2023_24_Datasets.xlsx`,
any `Status*.csv/json`, `tube_status.*`, `service_disruption.*`.

### 1.2 Register a TfL API key
Go to https://api-portal.tfl.gov.uk/ → sign up (free) → subscribe to the
"500 Requests per min" product → copy your **app_id** and **primary key**.

### 1.3 Add GitHub Secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret**
- `TFL_APP_ID` = your app id
- `TFL_APP_KEY` = your primary key

### 1.4 Give Actions permission to commit
**Settings → Actions → General → Workflow permissions** → select
**"Read and write permissions"** → Save. (Without this, the workflow can fetch
data but will fail to push it back to the repo.)

### 1.5 Trigger both workflows manually the first time
Don't wait for the cron schedule on day one:
- **Actions tab → "Live TfL Data Pipeline" → Run workflow → Run workflow**
- **Actions tab → "Live Economic Data (ONS)" → Run workflow → Run workflow**

The economic one takes a few minutes (it downloads a large ONS file the first time).

### 1.6 Verify data landed in the repo
After both runs go green, check `data/` in the repo — you should see all 9 CSVs
listed in the table below, plus `tfl_status_history.csv` and
`borough_economic_live.csv`. Open `borough_disruption_summary.csv` and confirm
it has real numbers, not empty columns.

### 1.7 Let it run a few cycles before building visuals
The TfL workflow runs every 15 min — let it fire 3–4 times so
`tfl_status_history.csv` has more than one timestamp in it. The trend chart
(`borough_disruption_daily.csv`) and the historical correlation only become
meaningful once there's more than one poll logged.

---

## Part 2 — Get your raw GitHub URLs

Every file Power BI needs follows this pattern:

```
https://raw.githubusercontent.com/<your-username>/<your-repo>/main/data/<filename>.csv
```

Replace `<your-username>` and `<your-repo>` once, then just swap the filename
for each entry in the table below. Keep this table open while you work through
Part 3 — it tells you exactly which file feeds which visual.

| File | What's in it | Use it for |
|---|---|---|
| `all_lines_combined.csv` | Every line's current status, latest poll only | "Live Status" visuals — status by mode, status mix, full line table |
| `disruption_enriched.csv` | Only the currently-disrupted lines, with cause + affected section | Disruption detail table |
| `borough_disruption_summary.csv` | One row per borough — current disruption rate, severity, GVA | Most of your report will use this — the core summary table |
| `disruption_cause_summary.csv` | Incidents grouped by root cause (signal failure, staff shortage, etc.) | Cause breakdown chart |
| `mode_disruption_summary.csv` | One row per mode (tube/dlr/overground/elizabeth-line) | Disruption rate by mode chart |
| `borough_disruption_daily.csv` | Borough × day — grows over time | **Trend line chart** — disruption rate over time by borough |
| `forecast_disruption_risk.csv` | Composite risk score + estimated GVA at risk, per borough | Risk score visuals, GVA-at-risk chart |
| `merged_transport_economic.csv` | Every line joined to its borough's GVA (row-level) | Only needed if you want line-level detail joined to economics; optional |
| `all_lines_history_enriched.csv` | Every poll, every line — full raw history | Optional — only if you want to build your own custom trend visuals beyond what `borough_disruption_daily.csv` gives you |

You do **not** need `tfl_status_history.csv` or `borough_economic_live.csv`
directly in Power BI — those are raw inputs that `build_dashboard_data.py`
already processes into the files above.

---

## Part 3 — Build the Power BI report

### 3.1 Connect the data
Open Power BI Desktop.
1. `Home → Get Data → Web`
2. Paste the raw URL for `borough_disruption_summary.csv` → `OK`
3. In the preview window, click `Transform Data` (not `Load` yet — you'll want to check types first)
4. Repeat steps 1–3 for each file in the table above that you plan to use. (Tip: once the first query works, right-click it in the Queries pane → `Duplicate`, then just edit the `Source` step's URL — faster than starting from scratch each time.)

### 3.2 Fix data types in Power Query Editor
For each table, click through and confirm:
- `borough`, `name`, `modeName`, `disruption_cause`, `risk_band`, `reason` → **Text**
- `total_gva_m`, `average_severity`, `disruption_rate_pct`, `composite_risk_score`, `estimated_gva_at_risk_m` → **Decimal Number**
- `disrupted_lines`, `lines_reported`, `statusSeverity`, `incidents` → **Whole Number**
- `date`, `timestamp` → **Date** or **Date/Time**
- `is_disrupted` → **True/False**

Rename queries to something short and clear (e.g. `Summary`, `CauseSummary`,
`ModeSummary`, `DailyTrend`, `Risk`, `Disruptions`, `AllLines`) — you'll be
referencing these names constantly while building visuals.

Click `Close & Apply` once everything looks right.

### 3.3 Build relationships
Go to **Model view** (left sidebar, the icon that looks like connected boxes).
Drag to connect on shared columns:
- `Summary[borough]` → `Risk[borough]` (one-to-one)
- `Summary[borough]` → `DailyTrend[borough]` (one-to-many)
- `AllLines[name]` → `Disruptions[name]` (one-to-many)

Set cardinality and cross-filter direction to **Single** for all of these
unless you have a specific reason to need both directions.

### 3.4 Build the visuals (mirrors the Streamlit tabs)

**Page 1 — Network Overview (KPI cards)**
- Card visuals from `Summary`: sum of `disrupted_lines`, average of
  `average_severity`, count of boroughs where `disrupted_lines > 0` (use a
  measure — see 3.5), sum of `estimated_gva_at_risk_m` from `Risk`.

**Page 2 — Live Status**
- Stacked bar: `AllLines`, X = `modeName`, Y = count of `name`, Legend =
  `severity_label`
- Donut chart: `AllLines`, Legend = `severity_label`, Values = count of `name`
- Table: `AllLines` — `name`, `modeName`, `statusSeverity`, `severity_label`,
  `borough`, `is_disrupted`, `reason`

**Page 3 — Disruption Analysis**
- Horizontal bar: `CauseSummary`, X = `incidents`, Y = `disruption_cause`,
  color by `avg_severity`
- Bar: `ModeSummary`, X = `modeName`, Y = `disruption_rate_pct`
- Table: `Disruptions` — `name`, `severity_label`, `disruption_cause`,
  `affected_section`, `reason`, `borough`
- Bar: `Summary`, X = `borough`, Y = `disruption_rate_pct`
- **Line chart (trend)**: `DailyTrend`, X = `date`, Y = `disruption_rate_pct`,
  Legend = `borough` — this is the one that gets better every day the
  workflow runs

**Page 4 — Economic Impact**
- Scatter: `Summary`, X = `total_gva_m`, Y = `average_severity`, size =
  `disrupted_lines`, color = `disruption_rate_pct`, details = `borough`
- Table: `Summary` — `borough`, `lines_reported`, `disrupted_lines`,
  `disruption_rate_pct`, `average_severity`, `total_gva_m`

**Page 5 — Forecast & Risk**
- Bar: `Risk`, X = `borough`, Y = `composite_risk_score`, color =
  `risk_band` (set a custom color rule: Critical=dark red, High=red,
  Medium=orange, Low=green, Very Low=light green — matches the Streamlit
  palette)
- Bar: `Risk`, X = `borough`, Y = `estimated_gva_at_risk_m`, color =
  `risk_band`
- Scatter: `Risk`, X = `total_gva_m`, Y = `composite_risk_score`, color =
  `risk_band`
- Table: `Risk` — all columns, sorted descending by `composite_risk_score`

### 3.5 A couple of useful DAX measures
```DAX
Disrupted Boroughs = CALCULATE(DISTINCTCOUNT(Summary[borough]), Summary[disrupted_lines] > 0)

Network Disruption Rate % =
DIVIDE(SUM(Summary[disrupted_lines]), SUM(Summary[lines_reported])) * 100
```

### 3.6 Add slicers
Add slicer visuals for `borough` and `modeName` at the top of each page (or
on a shared page if you're using Power BI's "sync slicers" feature) so your
report has the same filter behavior as the Streamlit sidebar.

---

## Part 4 — Publish and schedule refresh

1. `Home → Publish` → choose your workspace. (Needs Power BI Pro, Premium Per
   User, or a Premium-capacity workspace — scheduled refresh isn't available
   on a free "My Workspace".)
2. In the Power BI Service: open the dataset → **Settings → Scheduled refresh**
   → toggle **On**.
3. Because your source is a public `raw.githubusercontent.com` URL, **no
   gateway is required** — this only applies because the data is fetched
   from the public internet, not from a file on your machine.
4. Set refresh times. Power BI Pro allows up to 8 scheduled refreshes/day.
   A sensible cadence: every 3 hours, since your TfL workflow runs every 15
   min but the aggregated/trend files only meaningfully change a few times a
   day.
5. Click **Refresh now** once to confirm it pulls successfully before relying
   on the schedule.

---

## Part 5 — Ongoing maintenance

- **If a visual goes blank after publish**: almost always a data-type
  mismatch introduced by a schema change upstream. Re-open Power Query,
  check the "Detected columns" print in `fetch_economic_data.py`'s GitHub
  Actions log — if ONS changed a column name, that script will exit with an
  error and `borough_economic_live.csv` won't update, which cascades into
  `Risk` and `Summary` not refreshing either.
- **Check Action health regularly**: repo's **Actions** tab → both
  workflows should show recent green runs. A red run means check the logs —
  most common cause is a TfL API rate-limit or a temporary ONS outage; both
  workflows will just pick up cleanly on the next scheduled run.
- **Two different "live" speeds, by design**: your Streamlit dashboard's Tab
  1 hits the TfL API directly per visitor (true real-time). Power BI refreshes
  on its schedule (a few times a day). That split is intentional — Power BI
  isn't meant to compete with a live ticker, it's your trend/economic-impact
  reporting layer.
