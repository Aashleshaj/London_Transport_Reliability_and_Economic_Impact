from pathlib import Path
import pandas as pd
from scipy.stats import pearsonr

ROOT = Path(__file__).resolve().parent.parent
MERGED_PATH = ROOT / 'data' / 'merged_transport_economic.csv'
SUMMARY_PATH = ROOT / 'data' / 'borough_disruption_summary.csv'

merged_df = pd.read_csv(MERGED_PATH)

borough_summary = merged_df.groupby('borough', as_index=False).agg(
    average_severity=('statusSeverity', 'mean'),
    total_sales_m=('total_sales_m', 'first'),
    total_gva_m=('total_gva_m', 'first'),
    total_employees=('total_employees', 'first'),
    total_companies=('total_companies', 'first'),
    lines_reported=('name', 'nunique')
)

print('Borough Summary:')
print(borough_summary)

valid_gva = borough_summary.dropna(subset=['average_severity', 'total_gva_m'])
valid_employees = borough_summary.dropna(subset=['average_severity', 'total_employees'])

if len(valid_gva) >= 2:
    severity_vs_gva = pearsonr(valid_gva['average_severity'], valid_gva['total_gva_m'])
    print(f"\nCorrelation between average disruption severity and borough GVA: {severity_vs_gva[0]:.2f} (p-value: {severity_vs_gva[1]:.2f})")
else:
    print('\nNot enough boroughs with GVA data to calculate correlation.')

if len(valid_employees) >= 2:
    severity_vs_employees = pearsonr(valid_employees['average_severity'], valid_employees['total_employees'])
    print(f"Correlation between average disruption severity and borough employment: {severity_vs_employees[0]:.2f} (p-value: {severity_vs_employees[1]:.2f})")
else:
    print('Not enough boroughs with employment data to calculate correlation.')

borough_summary.to_csv(SUMMARY_PATH, index=False)
print(f"\nAnalysis complete. Summary saved to {SUMMARY_PATH}")