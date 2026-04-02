#!/usr/bin/env python3
"""
Cron Telemetry Importer — Import all Nova's cron run data into execution_logger DB.
Runs hourly, pulls data from all active cron jobs.
"""

import subprocess
import sys
from pathlib import Path

# Job IDs from openclaw cron list
CRON_JOBS = [
    "742fb399-07be-4a84-a98f-57364b3e3fa1",  # nova-watchdog-cron
    "aeb1b9b9-5487-4b6f-a3be-50a4cf6ee711",  # nova-signal-collector
    "797503a5-9996-4e27-95c2-184bdd47695d",  # nova-health-check
    "ea89ddfe-0f83-4a78-b3eb-f8f4991ccf67",  # nova-social-ping
    "f5db1b9c-0422-43fc-9cd6-15e9ea600627",  # daily-self-improver
]

SCRIPT_DIR = Path("/home/sntrblck/.openclaw/workspace/skills/advanced_memory")
LIMIT = 10  # Last 10 runs per job

def main():
    total_imported = 0
    total_skipped = 0
    
    for job_id in CRON_JOBS:
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "import_cron_runs.py"),
            "--job-id", job_id,
            "--limit", str(LIMIT)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout.strip()
        
        if "imported:" in output:
            # Parse "Done — imported: N, skipped (duplicates): M"
            try:
                parts = output.replace("Done — imported: ", "").split(", skipped (duplicates): ")
                imported = int(parts[0])
                skipped = int(parts[1].strip()) if len(parts) > 1 else 0
                total_imported += imported
                total_skipped += skipped
            except (ValueError, IndexError):
                pass  # Skip malformed output
    
    print(f"Telemetry: {total_imported} new, {total_skipped} duplicates")

if __name__ == "__main__":
    main()
