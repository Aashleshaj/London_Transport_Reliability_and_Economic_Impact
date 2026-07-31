"""
scripts/live_status_logger.py

Evolved version of fetch_data.py. Key differences:
  - Logs EVERY line on every poll (not just disrupted ones) — data_integration.py
    needs the full picture to compute disruption *rates*, not just counts.
  - Supports --once (single poll then exit) for use in GitHub Actions cron,
    and --loop (original schedule-based behaviour) for running locally/on a server.
  - Writes into data/tfl_status_history.csv, a single growing historical log that
    replaces Status.json / Status_all.csv / service_disruption.csv / tube_status.csv.

Usage:
    python scripts/live_status_logger.py --once          # single poll (for cron)
    python scripts/live_status_logger.py --loop           # continuous, every 5 min
    python scripts/live_status_logger.py --loop --interval 10

Environment variables (optional, raises TfL's 50 req/min anonymous limit):
    TFL_APP_ID
    TFL_APP_KEY   (your existing APP_KEY env var also still works)
"""
import argparse
import csv
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import schedule

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

LOG_FILE = DATA_DIR / "tfl_status_history.csv"

MODES_TO_CHECK = "tube,dlr,overground,elizabeth-line"

FIELDNAMES = [
    "timestamp", "date", "modeName", "name",
    "statusSeverity", "statusSeverityDescription", "reason",
    "disruptionDescription", "closureText",
]


def _auth_params() -> dict:
    app_id = os.getenv("TFL_APP_ID")
    app_key = os.getenv("TFL_APP_KEY") or os.getenv("APP_KEY")  # keep your old var working
    params = {}
    if app_id:
        params["app_id"] = app_id
    if app_key:
        params["app_key"] = app_key
    return params


def init_csv():
    """Create the history CSV with headers if it doesn't exist yet."""
    if not LOG_FILE.exists():
        with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()
        print(f"[{datetime.now():%H:%M:%S}] Created new history log: {LOG_FILE}")


def fetch_and_log_status():
    """Poll the TfL API once and append EVERY line's status to the history CSV."""
    url = f"https://api.tfl.gov.uk/Line/Mode/{MODES_TO_CHECK}/Status"
    params = {**_auth_params(), "detail": "true"}

    now = datetime.now(timezone.utc)
    print(f"[{now:%H:%M:%S}] Polling TfL API...")

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        rows_written, disrupted = 0, 0
        with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)

            for line in data:
                statuses = line.get("lineStatuses", [])
                status = statuses[0] if statuses else {}
                disruption = line.get("disruption") or (status.get("disruption") or {})

                status_code = status.get("statusSeverity")
                if status_code is not None and status_code != 10:
                    disrupted += 1

                writer.writerow({
                    "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "date": now.strftime("%Y-%m-%d"),
                    "modeName": line.get("modeName"),
                    "name": line.get("name"),
                    "statusSeverity": status_code,
                    "statusSeverityDescription": status.get("statusSeverityDescription"),
                    "reason": status.get("reason", ""),
                    "disruptionDescription": disruption.get("description", ""),
                    "closureText": disruption.get("closureText", ""),
                })
                rows_written += 1

        print(f"[{now:%H:%M:%S}] Logged {rows_written} lines "
              f"({disrupted} disrupted) → {LOG_FILE.name}")

    except requests.exceptions.RequestException as e:
        print(f"[{now:%H:%M:%S}] Error reaching TfL API: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true",
                         help="Poll once and exit (use this in GitHub Actions / cron)")
    parser.add_argument("--loop", action="store_true",
                         help="Poll continuously, like the original fetch_data.py")
    parser.add_argument("--interval", type=int, default=5,
                         help="Minutes between polls when --loop is used (default 5)")
    args = parser.parse_args()

    init_csv()
    fetch_and_log_status()  # always run once immediately

    if args.loop:
        schedule.every(args.interval).minutes.do(fetch_and_log_status)
        print(f"[{datetime.now():%H:%M:%S}] Scheduler started "
              f"(every {args.interval} min). Press Ctrl+C to exit.")
        while True:
            schedule.run_pending()
            time.sleep(1)
    # --once (or no flag) just exits after the single poll above —
    # this is the mode GitHub Actions will use.


if __name__ == "__main__":
    main()
