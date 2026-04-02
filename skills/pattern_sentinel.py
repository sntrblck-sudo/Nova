"""
Nova's Pattern Sentinel
=======================
Scans recent daily logs for recurring issues. If the same failure/advice
appears 3+ times without being resolved, it's a "stuck pattern" — needs a
structural fix, not another reflection.

Also tracks improving patterns — lessons that are working.
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
DAILY_LOGS_DIR = MEMORY_DIR / "daily_logs"
LESSONS_DIR = MEMORY_DIR / "lessons"
DB_PATH = MEMORY_DIR / "nova.db"
AUDIT_PATH = MEMORY_DIR / "sentinel_audit.jsonl"


def _audit(action: str, data: dict):
    entry = {"ts": datetime.utcnow().isoformat(), "action": action, **data}
    with open(AUDIT_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _read_daily_logs(days: int = 7) -> list:
    """Read all .jsonl daily log entries from the last N days."""
    entries = []
    cutoff = datetime.utcnow() - timedelta(days=days)

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


def _read_reflection_log(days: int = 7) -> list:
    """Read recent self-reflection entries."""
    reflections = []
    reflections_file = MEMORY_DIR / "self_reflections.md"

    if not reflections_file.exists():
        return reflections

    # Parse self_reflections.md for recent entries
    text = reflections_file.read_text()
    # Pull the last N days of entries from the file
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Split on ## headers and parse each entry
    import re
    entries = re.split(r"\n(?=## \d{4}-\d{2}-\d{2})", text)
    for entry in entries[-days:]:
        if not entry.strip():
            continue
        reflections.append(entry)

    return reflections


def _score_issue(issue_text: str) -> dict:
    """
    Classify an issue by type and suggest whether it's fixable by reflection.
    Returns: {fixable: bool, category: str, urgency: str}
    """
    issue_lower = issue_text.lower()

    categories = {
        "memory": ["memory", "remember", "forget", "recall", "context"],
        "communication": ["info-dump", "verbose", "explain", "too long", "concise"],
        "timing": ["late", "missed", "should have", "didn't ask"],
        "system": ["error", "crash", "fail", "broken", "bug"],
        "autonomy": ["ask", "approval", "permission", "couldn't"],
        "earning": ["earn", "monetize", "revenue", "opportunity"],
    }

    fixable_by_reflection = {
        "communication": True,
        "timing": True,
        "autonomy": True,
        "earning": True,
        "memory": True,
        "system": False,
    }

    found_category = "general"
    for cat, keywords in categories.items():
        if any(kw in issue_lower for kw in keywords):
            found_category = cat
            break

    urgency = "low"
    if any(kw in issue_lower for kw in ["error", "fail", "crash", "broken"]):
        urgency = "high"
    elif any(kw in issue_lower for kw in ["missed", "didn't", "should have"]):
        urgency = "medium"

    return {
        "category": found_category,
        "fixable_by_reflection": fixable_by_reflection.get(found_category, False),
        "urgency": urgency,
    }


def _detect_stuck_patterns(entries: list, threshold: int = 3) -> list:
    """
    Find issues that appear 3+ times across recent entries.
    Returns a list of stuck_pattern dicts.
    """
    issue_counts = defaultdict(lambda: {"count": 0, "first_seen": None, "last_seen": None, "entries": []})

    for entry in entries:
        issue = entry.get("issue") or entry.get("problem") or entry.get("failure_note", "")
        if not issue:
            continue

        # Normalize
        normalized = issue.strip().lower()[:100]

        info = issue_counts[normalized]
        info["count"] += 1
        info["last_seen"] = entry.get("ts", "")
        if not info["first_seen"]:
            info["first_seen"] = entry.get("ts", "")
        info["entries"].append(entry)

    stuck = []
    for issue_text, info in issue_counts.items():
        if info["count"] >= threshold:
            scored = _score_issue(issue_text)
            stuck.append({
                "issue": issue_text,
                "occurrences": info["count"],
                "first_seen": info["first_seen"],
                "last_seen": info["last_seen"],
                "category": scored["category"],
                "fixable_by_reflection": scored["fixable_by_reflection"],
                "urgency": scored["urgency"],
                "recommendation": _get_recommendation(scored, info["count"])
            })

    return stuck


def _get_recommendation(scored: dict, count: int) -> str:
    if not scored["fixable_by_reflection"]:
        return "Structural fix needed — reflection alone won't solve this"
    if scored["urgency"] == "high":
        return f"High urgency: appeared {count}x — address immediately in next session"
    if scored["category"] == "system":
        return f"System issue: requires tool/log investigation, not reflection"
    return f"Stuck pattern ({count}x) — need a concrete process change, not another reflection"


def _detect_improving_patterns() -> list:
    """
    Check recent application outcomes — lessons that are consistently
    showing improved=true are "working" patterns worth noting.
    """
    try:
        import sqlite3
    except ImportError:
        return []

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("""
        SELECT a.lesson_id, l.lesson, l.tags, l.confidence,
               COUNT(a.id) as app_count,
               SUM(a.improved) as improved_count
        FROM applications a
        JOIN lessons l ON a.lesson_id = l.id
        WHERE a.created_at >= datetime('now', '-7 days')
        GROUP BY a.lesson_id
        HAVING improved_count >= 1
        ORDER BY improved_count DESC
        LIMIT 5
    """)
    rows = cur.fetchall()
    conn.close()

    improving = []
    for r in rows:
        rate = r[5] / r[3] if r[3] else 0
        improving.append({
            "lesson_id": r[0],
            "lesson": r[1][:80],
            "tags": r[2],
            "confidence": r[3],
            "applications_7d": r[4],
            "improved_7d": r[5],
            "rate": round(rate, 2),
        })

    return improving


def run_sentinel(days: int = 7) -> dict:
    """
    Main sentinel run. Returns dict with:
      stuck_patterns: list
      improving_patterns: list
      stuck_count: int
      improving_count: int
      scan_summary: str
    """
    entries = _read_daily_logs(days)
    reflections = _read_reflection_log(days)

    # Combine failure_notes from reflections with daily log entries
    combined = list(entries)
    for ref in reflections:
        import re
        failures = re.findall(r"- failure_notes:?\s*\[(.*?)\]", ref, re.DOTALL)
        for failure_group in failures:
            for failure in failure_group.strip().split(","):
                failure = failure.strip().strip('"\'[]')
                if failure:
                    combined.append({"issue": failure, "type": "reflection_failure", "ts": ""})

    stuck = _detect_stuck_patterns(combined)
    improving = _detect_improving_patterns()

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "scan_days": days,
        "entries_scanned": len(combined),
        "stuck_patterns": stuck,
        "improving_patterns": improving,
        "stuck_count": len(stuck),
        "improving_count": len(improving),
        "scan_summary": _make_summary(stuck, improving),
    }

    _audit("sentinel_run", {
        "stuck_count": len(stuck),
        "improving_count": len(improving),
        "entries": len(combined)
    })

    return result


def _make_summary(stuck: list, improving: list) -> str:
    if not stuck and not improving:
        return "No stuck patterns or notable improving patterns detected."

    parts = []
    if stuck:
        high_urgency = [s for s in stuck if s["urgency"] == "high"]
        if high_urgency:
            parts.append(f"{len(high_urgency)} high-urgency stuck pattern(s)")
        medium = [s for s in stuck if s["urgency"] == "medium"]
        if medium:
            parts.append(f"{len(medium)} medium-urgency stuck pattern(s)")
        low = [s for s in stuck if s["urgency"] == "low"]
        if low:
            parts.append(f"{len(low)} persistent low-urgency pattern(s)")

    if improving:
        parts.append(f"{len(improving)} improving pattern(s)")

    return "; ".join(parts) if parts else "Scan complete."


def print_report(result: dict):
    """Pretty-print a sentinel report."""
    print(f"\n{'='*50}")
    print(f" Pattern Sentinel Report — {result['timestamp']}")
    print(f" Scanned {result['entries_scanned']} entries over {result['scan_days']} days")
    print(f"{'='*50}\n")

    print(f"📌 {result['scan_summary']}\n")

    if result["stuck_patterns"]:
        print(f"🚨 STUCK PATTERNS ({result['stuck_count']}):")
        for p in result["stuck_patterns"]:
            urgency_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(p["urgency"], "⚪")
            print(f"\n  {urgency_icon} [{p['category']}] {p['issue']}")
            print(f"     Occurred: {p['occurrences']}x | Fixable by reflection: {p['fixable_by_reflection']}")
            print(f"     → {p['recommendation']}")
    else:
        print("✅ No stuck patterns detected.")

    if result["improving_patterns"]:
        print(f"\n📈 IMPROVING PATTERNS ({result['improving_count']}):")
        for p in result["improving_patterns"]:
            print(f"\n  [{p['tags']}] {p['lesson']}")
            print(f"     Confidence: {p['confidence']} | 7d apps: {p['applications_7d']} | improved: {p['improved_7d']} ({p['rate']*100:.0f}%)")

    print()


if __name__ == "__main__":
    result = run_sentinel()
    print_report(result)
