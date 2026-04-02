"""
Nova's Pre-Session Brief
========================
Loaded at the start of each main session. Pulls:
1. Top 3 lessons relevant to recent context
2. Any stuck patterns requiring attention today
3. Yesterday's session highlights (from daily log)
4. Any unresolved decisions flagged for review

Format: concise, scannable. Not a wall of text.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
DAILY_LOGS_DIR = MEMORY_DIR / "daily_logs"
LESSONS_DIR = MEMORY_DIR / "lessons"
DB_PATH = MEMORY_DIR / "nova.db"


def _now():
    return datetime.utcnow()


def _read_recent_daily_logs(days: int = 2) -> list:
    """Read entries from the last N days of daily logs."""
    entries = []
    cutoff = _now() - timedelta(days=days)

    if not DAILY_LOGS_DIR.exists():
        return entries

    for log_file in sorted(DAILY_LOGS_DIR.glob("*.jsonl")):
        try:
            file_date = datetime.strptime(log_file.stem, "%Y-%m-%d")
            if file_date < cutoff:
                continue
        except ValueError:
            continue

        with open(log_file) as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return entries


def _get_stuck_patterns() -> list:
    """Get stuck patterns from most recent sentinel run, if any."""
    sentinel_log = MEMORY_DIR / "sentinel_latest.json"
    if sentinel_log.exists():
        try:
            data = json.loads(sentinel_log.read_text())
            return data.get("stuck_patterns", [])
        except json.JSONDecodeError:
            pass
    return []


def _get_yesterday_highlights() -> list:
    """Pull the session summary from yesterday's daily log."""
    yesterday = (_now() - timedelta(days=1)).strftime("%Y-%m-%d")
    log_file = DAILY_LOGS_DIR / f"{yesterday}.jsonl"
    highlights = []

    if log_file.exists():
        with open(log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "summary" and entry.get("note"):
                        highlights.append(entry["note"])
                except json.JSONDecodeError:
                    continue

    return highlights


def _infer_recent_topics(log_entries: list) -> list:
    """Guess what topics were active recently based on failure/issue tags."""
    topics = []
    for entry in log_entries:
        issue = entry.get("issue", "")
        if not issue:
            continue
        # Extract common topic keywords
        issue_lower = issue.lower()
        if any(k in issue_lower for k in ["telegram", "bot", "channel"]):
            topics.append("telegram")
        if any(k in issue_lower for k in ["earning", "wallet", "transaction", "tx"]):
            topics.append("earning")
        if any(k in issue_lower for k in ["memory", "context", "recall"]):
            topics.append("memory")
        if any(k in issue_lower for k in ["disk", "space", "storage", "disk"]):
            topics.append("disk")
        if any(k in issue_lower for k in ["cron", "schedule", "job"]):
            topics.append("system")
        if any(k in issue_lower for k in ["improve", "reflect", "lesson"]):
            topics.append("improvement")

    # Return most common
    return [t for t, _ in Counter(topics).most_common(3)]


def _get_relevant_lessons(topics: list, limit: int = 3) -> list:
    """Get lessons matching recent topics, sorted by confidence descending."""
    try:
        import sqlite3
    except ImportError:
        return []

    conn = sqlite3.connect(DB_PATH)
    results = []

    for topic in topics:
        cur = conn.execute(
            "SELECT id, lesson, tags, confidence FROM lessons WHERE context LIKE ? OR lesson LIKE ? OR tags LIKE ? ORDER BY confidence DESC LIMIT ?",
            (f"%{topic}%", f"%{topic}%", f"%{topic}%", 2)
        )
        for row in cur.fetchall():
            results.append({
                "id": row[0],
                "lesson": row[1][:100],
                "tags": row[2],
                "confidence": row[3]
            })

    conn.close()

    # Dedupe by id, keep top by confidence
    seen = set()
    unique = []
    for r in sorted(results, key=lambda x: x["confidence"], reverse=True):
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)

    return unique[:limit]


def _get_unresolved_decisions() -> list:
    """Check action_log.db for decisions with no choice logged yet."""
    try:
        import sqlite3
    except ImportError:
        return []

    action_db = MEMORY_DIR / "action_log.db"
    if not action_db.exists():
        return []

    conn = sqlite3.connect(action_db)
    cur = conn.execute(
        "SELECT id, decision_type, context FROM decisions WHERE choice IS NULL OR choice = '' OR choice = 'pending' LIMIT 5"
    )
    rows = cur.fetchall()
    conn.close()

    return [{"id": str(r[0]), "type": r[1], "context": r[2][:100]} for r in rows]


def build_brief() -> dict:
    """
    Build the pre-session brief. Returns a structured dict with:
      date, highlights, stuck_patterns, relevant_lessons, unresolved_decisions, topics
    """
    log_entries = _read_recent_daily_logs(3)
    topics = _infer_recent_topics(log_entries)
    yesterday = _get_yesterday_highlights()
    stuck = _get_stuck_patterns()
    lessons = _get_relevant_lessons(topics)
    decisions = _get_unresolved_decisions()

    return {
        "generated_at": _now().isoformat(),
        "date": _now().strftime("%Y-%m-%d"),
        "topics": topics,
        "yesterday_highlights": yesterday,
        "stuck_patterns": stuck[:3],  # top 3 only
        "relevant_lessons": lessons,
        "unresolved_decisions": decisions,
    }


def format_brief(brief: dict) -> str:
    """Format the brief as a readable multi-section string."""
    lines = [
        f"\n{'='*50}",
        f"📋 PRE-SESSION BRIEF — {brief['date']}",
        f"{'='*50}\n",
    ]

    if brief["topics"]:
        lines.append(f"Active topics: {', '.join(brief['topics'])}\n")

    if brief["yesterday_highlights"]:
        lines.append("📝 Yesterday's highlights:")
        for h in brief["yesterday_highlights"]:
            lines.append(f"  • {h}")
        lines.append("")

    if brief["stuck_patterns"]:
        lines.append("🚨 Attention needed (stuck patterns):")
        for p in brief["stuck_patterns"]:
            lines.append(f"  • [{p['category']}] {p['issue']}")
            lines.append(f"    → {p['recommendation']}")
        lines.append("")

    if brief["relevant_lessons"]:
        lines.append("💡 Relevant lessons (high confidence):")
        for l in brief["relevant_lessons"]:
            lines.append(f"  • [{l['tags']}] {l['lesson']} (conf: {l['confidence']})")
        lines.append("")

    if brief["unresolved_decisions"]:
        lines.append("⚠️ Unresolved decisions:")
        for d in brief["unresolved_decisions"]:
            lines.append(f"  • [{d['id']}] {d['description']}")
        lines.append("")

    lines.append(f"Generated: {brief['generated_at']}\n")
    return "\n".join(lines)


if __name__ == "__main__":
    brief = build_brief()
    print(format_brief(brief))
