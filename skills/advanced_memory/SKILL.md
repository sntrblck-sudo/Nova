# Advanced Memory System

## Description
A structured memory skill using a lightweight SQLite database for fast recall, tagging, and timestamp tracking. This system runs alongside the standard MEMORY.md file, ensuring old workflows remain intact while enabling faster querying and heartbeat checks.

## Commands

Use the exec tool to run the following Python commands:

* Remember something new:
```
python3 skills/advanced_memory/memory_manager.py remember "tag1,tag2" "The actual memory content to store"
```
* Recall memories by tag or keyword:
```
python3 skills/advanced_memory/memory_manager.py recall "tag1"
```
* Heartbeat (check what changed since a specific time):
```
python3 skills/advanced_memory/memory_manager.py heartbeat "YYYY-MM-DD HH:MM:SS"
```
* Forget a memory by ID:
```
python3 skills/advanced_memory/memory_manager.py forget <id>
```

## Guidelines
1. Always tag memories appropriately (e.g., people, events, preferences, tasks, alerts).
2. During your daily heartbeat or cron jobs, use the heartbeat command with the timestamp of your last run to quickly catch up on new alerts or changes.
3. **Note:** `remember` stores to SQLite only — it does NOT write to MEMORY.md. MEMORY.md updates happen only in the main session.