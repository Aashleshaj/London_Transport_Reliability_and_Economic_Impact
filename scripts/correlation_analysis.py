from pathlib import Path
import pandas as pd
from scipy.stats import pearsonr

ROOT = Path(__file__).resolve().parent.parent
MERGED_PATH = ROOT / 'data' / 'merged_transport_economic.csv'
SUMMARY_PATH = ROOT / 'data' / 'borough_disruption_summary.csv'

merged_df = pd.read_csv(MERGED_PATH)

borough_summary = merged_df.groupby('borough').agg(
    statusSeverity=('statusSeverity', 'mean'),
    average_income=('average_income', 'first'),
    employment_rate=('employment_rate', 'first'),
    lines_reported=('name', 'nunique')
).reset_index()

print('Borough Summary:')
print(borough_summary)

valid_income = borough_summary.dropna(subset=['statusSeverity', 'average_income'])
valid_employment = borough_summary.dropna(subset=['statusSeverity', 'employment_rate'])

if len(valid_income) >= 2:
    severity_vs_income = pearsonr(valid_income['statusSeverity'], valid_income['average_income'])
    print(f"\nCorrelation between average disruption severity and average income: {severity_vs_income[0]:.2f} (p-value: {severity_vs_income[1]:.2f})")
else:
    print('\nNot enough boroughs with income data to calculate correlation.')

if len(valid_employment) >= 2:
    severity_vs_employment = pearsonr(valid_employment['statusSeverity'], valid_employment['employment_rate'])
    print(f"Correlation between average disruption severity and employment rate: {severity_vs_employment[0]:.2f} (p-value: {severity_vs_employment[1]:.2f})")
else:
    print('Not enough boroughs with employment data to calculate correlation.')

borough_summary.to_csv(SUMMARY_PATH, index=False)
print(f"\nAnalysis complete. Summary saved to {SUMMARY_PATH}")