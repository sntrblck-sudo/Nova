#!/usr/bin/env python3
"""
Import OpenClaw cron run records into the execution_logger SQLite DB.
Target DB: /home/sntrblck/.openclaw/workspace/memory/execution_logs.db
Expected execution_logger schema fields: timestamp, event_type, session_key, task, outcome, tokens_used, error_msg

Example usage:
  python import_cron_runs.py --job-id f5db1b9c-0422-43fc-9cd6-15e9ea600627 --limit 50
Optional:
  python import_cron_runs.py --job-id <job-id> --limit 50 --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

DB_PATH = Path("/home/sntrblck/.openclaw/workspace/memory/execution_logs.db")
DEFAULT_EVENT_TYPE = "cron_run_import"


def run_openclaw_cron_runs(job_id: str, limit: int) -> list[dict[str, Any]]:
    """Run `openclaw cron runs` and return parsed JSON records."""
    cmd = ["openclaw", "cron", "runs", "--id", job_id, "--limit", str(limit)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"openclaw command failed with code {result.returncode}:\n{result.stderr.strip()}")
    
    stdout = result.stdout.strip()
    if not stdout:
        return []
    
    # Try normal JSON parse first
    try:
        parsed = json.loads(stdout)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            # Handle OpenClaw's wrapper format: {"entries": [...], "total": N, ...}
            if "entries" in parsed:
                return [item for item in parsed["entries"] if isinstance(item, dict)]
            return [parsed]
        raise ValueError("Unexpected JSON structure from openclaw cron runs.")
    except json.JSONDecodeError:
        pass
    
    # Fall back to NDJSON / line-by-line
    rows: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def ts_ms_to_iso_utc(ts_ms: int | float | None) -> str:
    """Convert epoch milliseconds to an ISO8601 UTC timestamp string."""
    if ts_ms is None:
        return dt.datetime.now(dt.timezone.utc).isoformat()
    return dt.datetime.fromtimestamp(ts_ms / 1000, tz=dt.timezone.utc).isoformat()


def map_run_to_execution_log(run: dict[str, Any]) -> dict[str, Any]:
    """Map one OpenClaw cron run record into execution_logger columns."""
    usage = run.get("usage") or {}
    job_id = run.get("jobId", "")
    action = run.get("action", "")
    status = run.get("status", "")
    delivered = run.get("delivered")
    delivery_status = run.get("deliveryStatus")
    duration_ms = run.get("durationMs")
    error = run.get("error")
    
    task = f"cron:{action}"
    if duration_ms is not None:
        task += f" durationMs={duration_ms}"
    if delivered is not None:
        task += f" delivered={delivered}"
    if delivery_status:
        task += f" deliveryStatus={delivery_status}"
    
    return {
        "timestamp": ts_ms_to_iso_utc(run.get("ts")),
        "event_type": DEFAULT_EVENT_TYPE,
        "session_key": job_id,
        "task": task,
        "outcome": status or "unknown",
        "tokens_used": int(usage.get("total_tokens") or 0),
        "error_msg": error,
    }


def ensure_table_exists(conn: sqlite3.Connection) -> None:
    """Create the table if it does not already exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event_type TEXT,
            session_key TEXT,
            task TEXT,
            outcome TEXT,
            tokens_used INTEGER,
            error_msg TEXT
        )
    """)
    conn.commit()


def row_exists(conn: sqlite3.Connection, row: dict[str, Any]) -> bool:
    """Avoid duplicate imports by matching on a stable combination of fields."""
    cur = conn.execute(
        """SELECT 1 FROM execution_logs WHERE timestamp = ? AND event_type = ? AND session_key = ? AND task = ? AND outcome = ? AND COALESCE(tokens_used, 0) = COALESCE(?, 0) AND COALESCE(error_msg, '') = COALESCE(?, '') LIMIT 1""",
        (
            row["timestamp"],
            row["event_type"],
            row["session_key"],
            row["task"],
            row["outcome"],
            row["tokens_used"],
            row["error_msg"],
        ),
    )
    return cur.fetchone() is not None


def import_runs(job_id: str, limit: int, dry_run: bool = False) -> tuple[int, int]:
    """Import cron runs for the given job. Returns (imported, skipped)."""
    runs = run_openclaw_cron_runs(job_id, limit)
    if not runs:
        print("No runs returned from openclaw cron runs.")
        return 0, 0
    
    conn = sqlite3.connect(DB_PATH)
    ensure_table_exists(conn)
    
    imported = 0
    skipped = 0
    
    for run in runs:
        log_row = map_run_to_execution_log(run)
        if dry_run:
            print(f"[DRY RUN] Would import: {log_row}")
            imported += 1
        else:
            if row_exists(conn, log_row):
                skipped += 1
                continue
            conn.execute(
                """INSERT INTO execution_logs (timestamp, event_type, session_key, task, outcome, tokens_used, error_msg) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    log_row["timestamp"],
                    log_row["event_type"],
                    log_row["session_key"],
                    log_row["task"],
                    log_row["outcome"],
                    log_row["tokens_used"],
                    log_row["error_msg"],
                ),
            )
            imported += 1
    
    if not dry_run:
        conn.commit()
    conn.close()
    
    return imported, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Import OpenClaw cron runs into execution_logger DB.")
    parser.add_argument("--job-id", required=True, help="OpenClaw cron job ID")
    parser.add_argument("--limit", type=int, default=50, help="Number of runs to fetch (default: 50)")
    parser.add_argument("--dry-run", action="store_true", help="Print rows without inserting")
    args = parser.parse_args()
    
    imported, skipped = import_runs(args.job_id, args.limit, args.dry_run)
    print(f"Done — imported: {imported}, skipped (duplicates): {skipped}")


if __name__ == "__main__":
    main()
