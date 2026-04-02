# Execution Logger Skill

## Description
Lightweight telemetry for Nova's execution. Logs task outcomes, token usage, errors, and performance to SQLite. Feeds data into the daily self-improver for RSO analysis.

## Log Events
Use the execution_logger to track what happened:

```
python3 skills/advanced_memory/execution_logger.py log <type> <task> <outcome> [tokens] [error]
```

### Event Types
- `session_start` — New session began
- `session_end` — Session ended
- `task_complete` — Task finished successfully
- `task_fail` — Task failed
- `cron_run` — Cron job executed
- `heartbeat` — Heartbeat check ran

### Outcomes
- `success` — Completed as expected
- `failure` — Failed but handled
- `error` — Unhandled error
- `skipped` — Skipped intentionally

## Get Summary
```bash
# Summary of today's activity
python3 skills/advanced_memory/execution_logger.py summary "YYYY-MM-DD HH:MM:SS"

# View recent logs
python3 skills/advanced_memory/execution_logger.py since "YYYY-MM-DD HH:MM:SS"
```

## Usage in Daily Self-Improver
The self-improver should call `summary` with yesterday's timestamp to analyze:
- Total events and outcomes
- Token usage trends
- Recurring errors
- Event type distribution

## DB Location
`memory/execution_logs.db`