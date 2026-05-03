from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
TRANSPORT_PATH = DATA_DIR / 'Status.csv'
ECONOMIC_CSV_PATH = DATA_DIR / 'economic_data.csv'
# ECONOMIC_JSON_PATH = DATA_DIR / 'economic_data.json'
MERGED_PATH = DATA_DIR / 'merged_transport_economic.csv'
SUMMARY_PATH = DATA_DIR / 'borough_disruption_summary.csv'

LINE_TO_BOROUGH = {
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


def normalize_borough_name(name: str) -> str:
    if pd.isna(name):
        return name
    borough = str(name).strip()
    borough = borough.replace(' City', '')
    return borough


def load_economic_data() -> pd.DataFrame:
    if ECONOMIC_CSV_PATH.exists():
        econ_df = pd.read_csv(ECONOMIC_CSV_PATH)
    # elif ECONOMIC_JSON_PATH.exists():
    #     econ_df = pd.read_json(ECONOMIC_JSON_PATH)
    else:
        raise FileNotFoundError(
            'No economic data found. Place data/economic_data.csv or data/economic_data.json in the data folder.'
        )

    if 'Borough' not in econ_df.columns:
        raise KeyError('economic_data file must contain a Borough column.')

    econ_df['Borough'] = econ_df['Borough'].apply(normalize_borough_name)
    return econ_df


def build_borough_economic_summary(econ_df: pd.DataFrame) -> pd.DataFrame:
    agg_dict = {
        'Sales £m': 'sum',
        'GVA £m': 'sum',
        'Export Total £m': 'sum',
        'Total Imports £m': 'sum',
        'Number of companies': 'sum',
        'Total Number of Employees': 'sum',
        'Forecast Sales 2024/25': 'mean',
        'Forecast Sales 2025/26': 'mean',
        'Forecast Sales 2026/27': 'mean',
        'Forecast Sales 2027/28': 'mean',
        'Forecast Sales 2028/29': 'mean'
    }

    available_cols = [col for col in agg_dict.keys() if col in econ_df.columns]
    if not available_cols:
        raise KeyError('No required numeric economic columns found in economic_data.csv.')

    agg = {col: agg_dict[col] for col in available_cols}
    borough_econ = econ_df.groupby('Borough', as_index=False).agg(agg)
    borough_econ = borough_econ.rename(columns={
        'Sales £m': 'total_sales_m',
        'GVA £m': 'total_gva_m',
        'Export Total £m': 'total_export_m',
        'Total Imports £m': 'total_imports_m',
        'Number of companies': 'total_companies',
        'Total Number of Employees': 'total_employees',
        'Forecast Sales 2024/25': 'forecast_sales_2024_25',
        'Forecast Sales 2025/26': 'forecast_sales_2025_26',
        'Forecast Sales 2026/27': 'forecast_sales_2026_27',
        'Forecast Sales 2027/28': 'forecast_sales_2027_28',
        'Forecast Sales 2028/29': 'forecast_sales_2028_29'
    })
    return borough_econ


def main():
    transport_df = pd.read_csv(TRANSPORT_PATH)
    transport_df['borough'] = transport_df['name'].map(LINE_TO_BOROUGH).fillna('Unknown')

    econ_df = load_economic_data()
    borough_econ = build_borough_economic_summary(econ_df)

    merged_df = transport_df.merge(
        borough_econ,
        left_on='borough',
        right_on='Borough',
        how='left'
    )

    if merged_df['Borough'].isna().any():
        missing = merged_df.loc[merged_df['Borough'].isna(), ['name', 'borough']].drop_duplicates()
        print('Warning: these transport lines could not be matched to an economic borough:')
        print(missing.to_string(index=False))

    merged_df.to_csv(MERGED_PATH, index=False)

    borough_summary = merged_df.groupby('borough', as_index=False).agg(
        lines_reported=('name', 'nunique'),
        average_severity=('statusSeverity', 'mean'),
        total_sales_m=('total_sales_m', 'first'),
        total_gva_m=('total_gva_m', 'first'),
        total_employees=('total_employees', 'first'),
        total_companies=('total_companies', 'first')
    )
    borough_summary.to_csv(SUMMARY_PATH, index=False)

    print('Data integration complete.')
    print(f'  Merged file: {MERGED_PATH}')
    print(f'  Borough summary: {SUMMARY_PATH}')


if __name__ == '__main__':
    main()
