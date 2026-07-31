import requests
import schedule
import time
import csv
from datetime import datetime
import os

# --- Configuration ---
# Replace with your TfL API Key
APP_KEY = os.getenv("APP_KEY")

# Target modes to check (tube, bus, dlr, overground, etc.)
MODES_TO_CHECK = "tube,dlr,overground,elizabeth-line"

# The CSV file where disruptions will be logged
LOG_FILE = "tfl_disruptions_log.csv"

def init_csv():
    """Create the CSV file and write headers if it doesn't exist."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Timestamp", 
                "Mode", 
                "Line Name", 
                "Status Code", 
                "Status Description", 
                "Reason"
            ])
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Created new log file: {LOG_FILE}")

def fetch_and_log_status():
    """Fetches the current status from TfL and logs disruptions."""
    url = f"https://api.tfl.gov.uk/Line/Mode/{MODES_TO_CHECK}/Status"
    params = {"app_key": APP_KEY}
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling TfL API...")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Raise an exception for bad status codes
        
        data = response.json()
        disruptions_found = 0
        
        with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            for line in data:
                line_name = line.get("name")
                mode_name = line.get("modeName")
                statuses = line.get("lineStatuses", [])
                
                if statuses:
                    # Status code 10 means "Good Service". Anything else is a disruption.
                    status_code = statuses[0].get("statusSeverity")
                    status_desc = statuses[0].get("statusSeverityDescription")
                    reason = statuses[0].get("reason", "No specific reason provided.")
                    
                    if status_code != 10:
                        disruptions_found += 1
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Log to CSV
                        writer.writerow([
                            timestamp, 
                            mode_name, 
                            line_name, 
                            status_code, 
                            status_desc, 
                            reason
                        ])
                        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Poll complete. Found {disruptions_found} disrupted lines.")
                        
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error reaching TfL API: {e}")

if __name__ == "__main__":
    init_csv()
    
    # Run immediately on startup
    fetch_and_log_status()
    
    # Schedule to run every 5 minutes
    schedule.every(5).minutes.do(fetch_and_log_status)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scheduler started. Press Ctrl+C to exit.")
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)