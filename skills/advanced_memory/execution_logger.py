"""
Execution Logger for OpenClaw Agent (Nova)
Logs task outcomes, token usage, errors, and performance metrics.
Designed to feed data into the daily self-improver for RSO.
"""

import sqlite3
import sys
import os
from datetime import datetime
from typing import Optional

DB_PATH = '/home/sntrblck/.openclaw/workspace/memory/execution_logs.db'

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS execution_logs
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    event_type TEXT,
    session_key TEXT,
    task TEXT,
    outcome TEXT,
    tokens_used INTEGER,
    error_msg TEXT,
    metadata TEXT)''')
    return conn

def log_event(
    event_type: str,
    task: str,
    outcome: str,
    session_key: str = "main",
    tokens_used: int = 0,
    error_msg: str = "",
    metadata: str = ""
):
    """
    Log an execution event.
    
    event_type: session_start | session_end | task_complete | task_fail | cron_run | heartbeat
    task: What was being done
    outcome: success | failure | error | skipped
    tokens_used: Token count if available
    """
    conn = get_connection()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn.execute("""INSERT INTO execution_logs 
    (timestamp, event_type, session_key, task, outcome, tokens_used, error_msg, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
    (timestamp, event_type, session_key, task, outcome, tokens_used, error_msg, metadata))
    conn.commit()
    conn.close()

def get_logs_since(since_timestamp: str, limit: int = 100):
    """Get all logs since a given timestamp for analysis."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT id, timestamp, event_type, task, outcome, tokens_used, error_msg 
    FROM execution_logs WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?""",
    (since_timestamp, limit))
    results = cursor.fetchall()
    conn.close()
    return results

def get_session_summary(since_timestamp: str):
    """Get a summary of session activity for analysis."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total events
    cursor.execute("SELECT COUNT(*) FROM execution_logs WHERE timestamp >= ?", (since_timestamp,))
    total_events = cursor.fetchone()[0]
    
    # By outcome
    cursor.execute("""SELECT outcome, COUNT(*) FROM execution_logs 
    WHERE timestamp >= ? GROUP BY outcome""", (since_timestamp,))
    outcomes = dict(cursor.fetchall())
    
    # By event type
    cursor.execute("""SELECT event_type, COUNT(*) FROM execution_logs 
    WHERE timestamp >= ? GROUP BY event_type""", (since_timestamp,))
    event_types = dict(cursor.fetchall())
    
    # Total tokens used
    cursor.execute("SELECT SUM(tokens_used) FROM execution_logs WHERE timestamp >= ?", (since_timestamp,))
    total_tokens = cursor.fetchone()[0] or 0
    
    # Errors
    cursor.execute("""SELECT error_msg, COUNT(*) FROM execution_logs 
    WHERE timestamp >= ? AND error_msg != '' GROUP BY error_msg""", (since_timestamp,))
    errors = dict(cursor.fetchall())
    
    conn.close()
    
    return {
        "total_events": total_events,
        "outcomes": outcomes,
        "event_types": event_types,
        "total_tokens": total_tokens,
        "errors": errors
    }

def clear_logs_before(before_timestamp: str):
    """Clear old logs to prevent unbounded growth. Keep recent."""
    conn = get_connection()
    conn.execute("DELETE FROM execution_logs WHERE timestamp < ?", (before_timestamp,))
    conn.commit()
    deleted = conn.total_changes
    conn.close()
    return deleted

# CLI interface
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 execution_logger.py <command> [args]")
        print("Commands:")
        print("  log <type> <task> <outcome> [tokens] [error]")
        print("  since <timestamp>")
        print("  summary <timestamp>")
        print("  clear <before_timestamp>")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "log" and len(sys.argv) >= 4:
        event_type = sys.argv[2]
        task = sys.argv[3]
        outcome = sys.argv[4]
        tokens = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        error_msg = sys.argv[6] if len(sys.argv) > 6 else ""
        log_event(event_type, task, outcome, tokens_used=tokens, error_msg=error_msg)
        print(f"Logged: [{event_type}] {task} -> {outcome}")
    
    elif command == "since" and len(sys.argv) >= 3:
        logs = get_logs_since(sys.argv[2])
        for row in logs:
            print(row)
    
    elif command == "summary" and len(sys.argv) >= 3:
        summary = get_session_summary(sys.argv[2])
        import json
        print(json.dumps(summary, indent=2))
    
    elif command == "clear" and len(sys.argv) >= 3:
        deleted = clear_logs_before(sys.argv[2])
        print(f"Cleared {deleted} old log entries")
    
    else:
        print("Invalid command or missing arguments")