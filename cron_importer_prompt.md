# Cron Log Importer for RSO Telemetry

## Goal
Build a script that pulls data from `openclaw cron runs` and imports it into the execution_logger SQLite DB.

## Background
We have two systems:
1. **execution_logger.py** — SQLite DB at `/home/sntrblck/.openclaw/workspace/memory/execution_logs.db`. Logs events with: timestamp, event_type, session_key, task, outcome, tokens_used, error_msg
2. **openclaw cron runs** — Can be queried via: `openclaw cron runs --id <job-id> --limit <n>`

The cron run output looks like:
```json
{
  "ts": 1774616627032,
  "jobId": "f5db1b9c-0422-43fc-9cd6-15e9ea600627",
  "action": "finished",
  "status": "ok",
  "error": null,
  "durationMs": 226980,
  "usage": {"input_tokens": 74683, "output_tokens": 2609, "total_tokens": 17585},
  "delivered": true,
  "deliveryStatus": "delivered"
}
```

## What to build

A Python script (`cron_log_importer.py`) that:
1. Accepts a job ID and optionally a time range
2. Calls `openclaw cron runs --id <job-id>` via subprocess
3. Parses the JSON output
4. Imports each cron run into execution_logger with:
   - `event_type`: "cron_run"
   - `task`: job name (if available) or job ID
   - `outcome`: map "status": "ok"→"success", "error"→"failure"
   - `tokens_used`: from usage.total_tokens
   - `error_msg`: from error field if present
   - `timestamp`: from ts field (epoch ms)
   - `session_key`: can be empty or the job ID
5. Avoids duplicate imports (check if entry already exists by ts+jobId)
6. Has a CLI interface:
   ```
   python3 cron_log_importer.py import <job-id> [--limit 10]
   python3 cron_log_importer.py import-all  # import all cron jobs
   ```

## Constraints
- Use existing execution_logger DB schema
- Use subprocess to call openclaw CLI
- Parse JSON output from stdout
- Store DB at `/home/sntrblck/.openclaw/workspace/memory/execution_logs.db`

## Deliverables
- `cron_log_importer.py` in `/home/sntrblck/.openclaw/workspace/skills/advanced_memory/`
- Working CLI that successfully imports cron runs into the DB

## Testing
After building, run:
```
python3 skills/advanced_memory/cron_log_importer.py import f5db1b9c-0422-43fc-9cd6-15e9ea600627 --limit 5
```
Then verify with:
```
python3 skills/advanced_memory/execution_logger.py since "2026-03-27 00:00:00"
```