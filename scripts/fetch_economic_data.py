"""
scripts/fetch_economic_data.py

Replaces the manually-downloaded kMatrix_LCEGS spreadsheet with an
automated pull from the Office for National Statistics.

Honesty note: GVA is data the UK government only publishes annually —
that's true regardless of source (ONS, GLA, anywhere). There is no
"real-time GVA". What this script makes live is *how* you get it: it
pulls the latest published ONS release over HTTP automatically, instead
of a person downloading a spreadsheet and committing it to the repo by
hand. Re-run this periodically (see the weekly cron in the workflow)
and it will always reflect whatever ONS has most recently published —
no manual step required.

Source: https://www.ons.gov.uk/datasets/gva-by-industry-by-local-authority

Usage:
    python scripts/fetch_economic_data.py
    python scripts/fetch_economic_data.py --force   # ignore cached raw download
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

CSV_URL = ("https://download.ons.gov.uk/downloads/datasets/"
           "gva-by-industry-by-local-authority/editions/time-series/versions/1.csv")

RAW_CACHE = DATA_DIR / "_ons_gva_raw.csv"   # large (~250MB) — gitignore this one
OUT_PATH  = DATA_DIR / "borough_economic_live.csv"

LONDON_BOROUGHS = [
    "Barking and Dagenham", "Barnet", "Bexley", "Brent", "Bromley", "Camden",
    "Croydon", "Ealing", "Enfield", "Greenwich", "Hackney",
    "Hammersmith and Fulham", "Haringey", "Harrow", "Havering", "Hillingdon",
    "Hounslow", "Islington", "Kensington and Chelsea", "Kingston upon Thames",
    "Lambeth", "Lewisham", "Merton", "Newham", "Redbridge",
    "Richmond upon Thames", "Southwark", "Sutton", "Tower Hamlets",
    "Waltham Forest", "Wandsworth", "Westminster, City of", "City of London",
]


def download_csv(dest: Path) -> Path:
    print("Downloading ONS GVA-by-local-authority dataset (large file, may take a while)...")
    with requests.get(CSV_URL, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    print(f"  saved to {dest}")
    return dest


def detect_columns(df: pd.DataFrame) -> dict:
    """
    ONS occasionally renames columns between releases, so we detect them
    by pattern rather than hardcode.
    """
    cols = {c.lower(): c for c in df.columns}
    
    # UPDATED: Added fallback to look exactly for 'geography' or 'administrative-geography'
    area_col = (next((cols[k] for k in cols if "area" in k and "name" in k), None)
                or next((cols[k] for k in cols if "geography" in k and "name" in k), None)
                or cols.get("geography") 
                or cols.get("administrative-geography"))
                
    value_col = (next((cols[k] for k in cols if k in ("value", "v4_1", "obs_value")), None)
                 or next((cols[k] for k in cols if "value" in k), None))
    
    year_col = next((cols[k] for k in cols if k in ("time", "year", "date")), None)
    
    industry_col = next((cols[k] for k in cols if "industry" in k or "sic" in k), None)

    found = {"area": area_col, "value": value_col, "year": year_col, "industry": industry_col}
    print(f"  Detected columns: {found}")
    
    missing = [k for k, v in found.items() if v is None and k != "industry"]
    if missing:
        print(f"  ⚠ Could not auto-detect required columns: {missing}")
        print(f"  Actual columns in the file: {list(df.columns)}")
        print("  Update the detect_columns() patterns above to match, then re-run.")
        sys.exit(1)
        
    return found

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    args = parser.parse_args()

    if args.force or not RAW_CACHE.exists():
        download_csv(RAW_CACHE)
    else:
        print(f"Using cached download at {RAW_CACHE} (pass --force to re-fetch)")

    print("Reading + filtering to London boroughs...")
    df = pd.read_csv(RAW_CACHE, low_memory=False)
    cols = detect_columns(df)

    df = df[df[cols["area"]].isin(LONDON_BOROUGHS)]
    if df.empty:
        print("⚠ No London boroughs matched — the area-name column format may have "
              "changed. Check detect_columns() output above.")
        sys.exit(1)

    # Keep only the total-economy row per borough per year, if an industry
    # breakdown column exists (this dataset normally has one).
    if cols["industry"]:
        total_labels = [v for v in df[cols["industry"]].unique()
                         if str(v).strip().lower() in ("total", "all industries", "a-t")]
        if total_labels:
            df = df[df[cols["industry"]].isin(total_labels)]

    latest_year = df[cols["year"]].max()
    latest = df[df[cols["year"]] == latest_year].copy()

    latest["Borough"] = (
        latest[cols["area"]]
        .str.replace(", City of", "", regex=False)
        .str.replace("City of ", "", regex=False)
    )
    latest = latest.rename(columns={cols["value"]: "total_gva_m"})
    latest["total_gva_m"] = pd.to_numeric(latest["total_gva_m"], errors="coerce")

    out = latest.groupby("Borough", as_index=False)["total_gva_m"].sum()
    out["gva_year"] = latest_year
    out.to_csv(OUT_PATH, index=False)
    print(f"\n✅ {OUT_PATH.name}: {len(out)} London boroughs, GVA year {latest_year}")


if __name__ == "__main__":
    main()
