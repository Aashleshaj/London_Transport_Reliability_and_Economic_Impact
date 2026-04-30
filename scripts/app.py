import pandas as pd
import json
import os
from datetime import datetime

def extract_date(timestamp_str):
    """
    Extract date from ISO 8601 timestamp (e.g., '2026-03-31T11:01:31.293Z' -> '2026-03-31')
    """
    if not timestamp_str or timestamp_str == '0001-01-01T00:00:00':
        return None
    try:
        # Parse the timestamp and return just the date
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.date().isoformat()
    except (ValueError, AttributeError):
        return None

# Function to convert JSON to CSV, extracting statusSeverityDescription from lineStatuses
def json_to_csv_extract_status(json_file_path, csv_file_path):
    """
    Converts JSON to CSV and extracts statusSeverityDescription from lineStatuses array.
    Handles various JSON structures and empty files gracefully.
    """
    try:
        with open(json_file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"  - Invalid JSON format in {json_file_path}")
        return None
    except FileNotFoundError:
        print(f"  - File not found: {json_file_path}")
        return None

    # Check if data is empty
    if not data:
        print(f"  - Empty JSON file: {json_file_path}")
        return pd.DataFrame()

    # Process the data
    rows = []
    
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue  # Skip non-dict items
                
            row = {
                'name': item.get('name'),
                'modeName': item.get('modeName'),
                'date': extract_date(item.get('modified')),
            }
            
            # Extract statusSeverityDescription from lineStatuses
            line_statuses = item.get('lineStatuses', [])
            if line_statuses and isinstance(line_statuses, list):
                # Get the first lineStatus entry
                status = line_statuses[0]
                row['statusSeverity'] = status.get('statusSeverity')
                row['statusSeverityDescription'] = status.get('statusSeverityDescription')
                row['reason'] = status.get('reason', '')
            else:
                row['statusSeverity'] = None
                row['statusSeverityDescription'] = None
                row['reason'] = ''

            # Extract from disruption if it exists
            disruption = item.get('disruption')
            if disruption and isinstance(disruption, dict):
                row['disruptionDescription'] = disruption.get('description')
                row['closureText'] = disruption.get('closureText')
            else:
                row['disruptionDescription'] = None
                row['closureText'] = None

            rows.append(row)
    else:
        print(f"  - Unexpected JSON structure in {json_file_path} (expected list)")
        return None
    
    # Create DataFrame
    if not rows:
        print(f"  - No valid records found in {json_file_path}")
        return pd.DataFrame()
        
    df = pd.DataFrame(rows)
    
    # Save to CSV
    df.to_csv(csv_file_path, index=False)
    return df


# Example usage
data_dir = '../data'
output_dir = '../data'

# Get all JSON files in data directory
json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]

print(f"Found {len(json_files)} JSON files: {json_files}")

# Process each JSON file
for json_file in json_files:
    json_path = os.path.join(data_dir, json_file)
    csv_file = json_file.replace('.json', '.csv')
    csv_path = os.path.join(output_dir, csv_file)
    
    try:
        print(f"\nProcessing {json_file}...")
        df = json_to_csv_extract_status(json_path, csv_path)
        
        if df is not None and not df.empty:
            print(f"✓ Successfully converted {json_file} to {csv_file}")
            print(f"  - Records: {len(df)}")
            print(f"  - Columns: {list(df.columns)}")
        else:
            print(f"⚠ {json_file} appears to be empty or invalid")
            
    except Exception as e:
        print(f"✗ Error processing {json_file}: {str(e)}")

print("\n✓ All JSON files processed!")