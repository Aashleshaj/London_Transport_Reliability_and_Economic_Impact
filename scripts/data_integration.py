from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TRANSPORT_PATH = DATA_DIR / "Status.csv"
ECONOMIC_CSV_PATH = DATA_DIR / "economic_data.csv"
ECONOMIC_JSON_PATH = DATA_DIR / "economic_data.json"
MERGED_PATH = DATA_DIR / "merged_transport_economic.csv"
SUMMARY_PATH = DATA_DIR / "borough_disruption_summary.csv"

transport_df = pd.read_csv(TRANSPORT_PATH)

if ECONOMIC_CSV_PATH.exists():
    economic_df = pd.read_csv(ECONOMIC_CSV_PATH)
elif ECONOMIC_JSON_PATH.exists():
    economic_df = pd.read_json(ECONOMIC_JSON_PATH)
else:
    raise FileNotFoundError(
        'No economic data found. Place either data/economic_data.csv or data/economic_data.json in the project data folder.'
    )

# Simplified line-to-borough mapping for sample analysis.
line_to_borough = {
    'Bakerloo': 'Westminster',
    'Central': 'Islington',
    'Circle': 'Westminster',
    'District': 'Westminster',
    'Hammersmith & City': 'Westminster',
    'Jubilee': 'Westminster',
    'Metropolitan': 'Westminster',
    'Northern': 'Camden',
    'Piccadilly': 'Westminster',
    'Victoria': 'Westminster',
    'Waterloo & City': 'Westminster'
}

transport_df['borough'] = transport_df['name'].map(line_to_borough).fillna('Unknown')

merged_df = transport_df.merge(economic_df, on='borough', how='left')
merged_df.to_csv(MERGED_PATH, index=False)

missing_boroughs = sorted(set(transport_df.loc[transport_df['borough'] == 'Unknown', 'name']))
if missing_boroughs:
    print('Warning: these lines have no borough mapping:', missing_boroughs)

missing_economic = merged_df.loc[merged_df[['average_income', 'employment_rate']].isna().any(axis=1)]
if not missing_economic.empty:
    print('Warning: some merged rows have missing economic data for boroughs:')
    print(missing_economic[['name', 'borough']].drop_duplicates())

borough_summary = merged_df.groupby('borough').agg(
    lines_reported=('name', 'nunique'),
    average_severity=('statusSeverity', 'mean'),
    average_income=('average_income', 'first'),
    employment_rate=('employment_rate', 'first')
).reset_index()

borough_summary.to_csv(SUMMARY_PATH, index=False)

print('Data integration complete.')
print(f'  Merged data: {MERGED_PATH}')
print(f'  Borough summary: {SUMMARY_PATH}')