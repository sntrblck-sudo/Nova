"""
Nova's Lesson Manager
=====================
Structured lesson storage with confidence tracking and application history.
Supports both flat-file (JSON) and SQLite mirrors for reliability.

Tables:
  - lessons: id, context, lesson, applied, tags, confidence, created_at, updated_at
  - applications: id, lesson_id, session_date, applied_context, outcome, improved, created_at
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
LESSONS_DIR = MEMORY_DIR / "lessons"
LESSONS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = MEMORY_DIR / "nova.db"
AUDIT_PATH = MEMORY_DIR / "lesson_audit.jsonl"


def _get_db():
    """Get SQLite connection with schema init."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id TEXT PRIMARY KEY,
            context TEXT NOT NULL,
            lesson TEXT NOT NULL,
            applied TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            confidence REAL DEFAULT 0.5,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            lesson_id TEXT,
            session_date TEXT,
            applied_context TEXT DEFAULT '',
            outcome TEXT DEFAULT '',
            improved INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    return conn


def _lesson_path(lesson_id: str) -> Path:
    return LESSONS_DIR / f"{lesson_id}.json"


def _audit(action: str, data: dict):
    """Append to audit log."""
    entry = {"ts": datetime.utcnow().isoformat(), "action": action, **data}
    with open(AUDIT_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _now():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _tags_to_json(tags) -> str:
    if isinstance(tags, list):
        return json.dumps(tags)
    return tags


def _tags_from_json(tags_str: str) -> list:
    try:
        return json.loads(tags_str)
    except (TypeError, json.JSONDecodeError):
        return []


# ─── CRUD ────────────────────────────────────────────────────────────────────

def add_lesson(context: str, lesson: str, applied: str = "", tags: list = None) -> str:
    """Add a new lesson. Returns lesson_id."""
    lid = f"lesson_{uuid.uuid4().hex[:12]}"
    now = _now()

    conn = _get_db()
    conn.execute(
        "INSERT INTO lessons (id, context, lesson, applied, tags, confidence, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (lid, context, lesson, applied, _tags_to_json(tags or []), 0.5, now, now)
    )
    conn.commit()
    conn.close()

    # Also write flat file
    _lesson_path(lid).write_text(json.dumps({
        "id": lid, "context": context, "lesson": lesson,
        "applied": applied, "tags": tags or [], "confidence": 0.5,
        "created_at": now, "updated_at": now
    }, indent=2))

    _audit("add", {"lesson_id": lid, "tags": tags or []})
    return lid


def get_lesson(lesson_id: str) -> Optional[dict]:
    """Get a lesson by ID. Returns dict or None."""
    conn = _get_db()
    cur = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0], "context": row[1], "lesson": row[2], "applied": row[3],
        "tags": _tags_from_json(row[4]), "confidence": row[5],
        "created_at": row[6], "updated_at": row[7]
    }


def update_lesson(lesson_id: str, outcome: str = None, improved: bool = None) -> bool:
    """Update a lesson's outcome and optionally bump/drop confidence."""
    lesson = get_lesson(lesson_id)
    if not lesson:
        return False

    now = _now()
    new_conf = lesson["confidence"]

    if improved is not None:
        if improved:
            new_conf = min(1.0, lesson["confidence"] + 0.15)
        else:
            new_conf = max(0.0, lesson["confidence"] - 0.1)

    conn = _get_db()
    conn.execute(
        "UPDATE lessons SET updated_at = ?, confidence = ? WHERE id = ?",
        (now, new_conf, lesson_id)
    )
    conn.commit()
    conn.close()

    # Update flat file
    fp = _lesson_path(lesson_id)
    if fp.exists():
        data = json.loads(fp.read_text())
        data["updated_at"] = now
        data["confidence"] = new_conf
        fp.write_text(json.dumps(data, indent=2))

    _audit("update", {"lesson_id": lesson_id, "confidence": new_conf, "outcome": outcome})
    return True


def get_all_lessons() -> list:
    """Return all lessons as dicts."""
    conn = _get_db()
    cur = conn.execute("SELECT * FROM lessons ORDER BY confidence DESC, created_at DESC")
    rows = cur.fetchall()
    conn.close()

    return [
        {"id": r[0], "context": r[1], "lesson": r[2], "applied": r[3],
         "tags": _tags_from_json(r[4]), "confidence": r[5],
         "created_at": r[6], "updated_at": r[7]}
        for r in rows
    ]


def get_top_lessons(limit: int = 5, min_confidence: float = 0.0) -> list:
    """Get highest-confidence lessons above a threshold."""
    conn = _get_db()
    cur = conn.execute(
        "SELECT * FROM lessons WHERE confidence >= ? ORDER BY confidence DESC, created_at DESC LIMIT ?",
        (min_confidence, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "context": r[1], "lesson": r[2], "applied": r[3],
         "tags": _tags_from_json(r[4]), "confidence": r[5],
         "created_at": r[6], "updated_at": r[7]}
        for r in rows
    ]


def search_lessons(query: str, limit: int = 5) -> list:
    """Full-text-ish search across context and lesson text."""
    conn = _get_db()
    cur = conn.execute(
        "SELECT * FROM lessons WHERE context LIKE ? OR lesson LIKE ? ORDER BY confidence DESC LIMIT ?",
        (f"%{query}%", f"%{query}%", limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "context": r[1], "lesson": r[2], "applied": r[3],
         "tags": _tags_from_json(r[4]), "confidence": r[5],
         "created_at": r[6], "updated_at": r[7]}
        for r in rows
    ]


def get_lessons_by_tag(tag: str) -> list:
    """Get lessons with a specific tag."""
    conn = _get_db()
    cur = conn.execute("SELECT * FROM lessons ORDER BY confidence DESC")
    rows = cur.fetchall()
    conn.close()

    results = []
    for r in rows:
        tags = _tags_from_json(r[4])
        if tag in tags:
            results.append({
                "id": r[0], "context": r[1], "lesson": r[2], "applied": r[3],
                "tags": tags, "confidence": r[5], "created_at": r[6], "updated_at": r[7]
            })
    return results


# ─── Application Logging ───────────────────────────────────────────────────────

def log_application(lesson_id: str, session_date: str, applied_context: str = "", outcome: str = "") -> str:
    """Log that a lesson was applied in a session. Returns log_id."""
    lid = f"app_{uuid.uuid4().hex[:12]}"
    now = _now()

    conn = _get_db()
    conn.execute(
        "INSERT INTO applications (id, lesson_id, session_date, applied_context, outcome, improved, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (lid, lesson_id, session_date, applied_context, outcome, 0, now)
    )
    conn.commit()
    conn.close()

    _audit("application_log", {
        "application_id": lid, "lesson_id": lesson_id,
        "session_date": session_date, "outcome": outcome
    })
    return lid


def resolve_application(application_id: str, outcome: str, improved: bool) -> bool:
    """Mark an application with its outcome and update lesson confidence."""
    conn = _get_db()
    conn.execute(
        "UPDATE applications SET outcome = ?, improved = ? WHERE id = ?",
        (outcome, 1 if improved else 0, application_id)
    )
    conn.commit()
    conn.close()

    _audit("application_resolved", {
        "application_id": application_id, "outcome": outcome, "improved": improved
    })
    return True


def get_recent_applications(days: int = 7) -> list:
    """Get application logs from recent days."""
    conn = _get_db()
    cur = conn.execute(
        "SELECT * FROM applications ORDER BY created_at DESC LIMIT ?",
        (days * 10,)  # assume at most 10 apps per day
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "lesson_id": r[1], "session_date": r[2],
         "applied_context": r[3], "outcome": r[4], "improved": bool(r[5]), "created_at": r[6]}
        for r in rows
    ]


def get_lesson_applications(lesson_id: str) -> list:
    """Get all applications for a specific lesson."""
    conn = _get_db()
    cur = conn.execute(
        "SELECT * FROM applications WHERE lesson_id = ? ORDER BY created_at DESC",
        (lesson_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "lesson_id": r[1], "session_date": r[2],
         "applied_context": r[3], "outcome": r[4], "improved": bool(r[5]), "created_at": r[6]}
        for r in rows
    ]


# ─── Summary ─────────────────────────────────────────────────────────────────

def get_summary() -> dict:
    """Quick summary stats for dashboarding."""
    conn = _get_db()
    cur = conn.execute("SELECT COUNT(*), AVG(confidence), MAX(confidence) FROM lessons")
    count, avg_conf, max_conf = cur.fetchone()

    cur2 = conn.execute("SELECT COUNT(*) FROM applications WHERE improved = 1")
    improved = cur2.fetchone()[0]

    cur3 = conn.execute("SELECT COUNT(*) FROM applications")
    total_apps = cur3.fetchone()[0]
    conn.close()

    return {
        "total_lessons": count or 0,
        "avg_confidence": round(avg_conf or 0, 3),
        "max_confidence": round(max_conf or 0, 3),
        "applications_total": total_apps or 0,
        "applications_improved": improved or 0,
        "improvement_rate": round(improved / total_apps, 3) if total_apps else 0,
    }


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"

    if cmd == "summary":
        print(json.dumps(get_summary(), indent=2))
    elif cmd == "list":
        for l in get_all_lessons():
            print(f"[{l['id']}] conf={l['confidence']} tags={l['tags']}")
            print(f"  context: {l['context'][:80]}")
            print(f"  lesson:  {l['lesson'][:80]}")
            print()
    elif cmd == "add":
        if len(sys.argv) < 4:
            print("Usage: lesson_manager.py add <context> <lesson> [tag1,tag2]")
            sys.exit(1)
        context, lesson = sys.argv[2], sys.argv[3]
        tags = [t.strip() for t in sys.argv[4].split(",")] if len(sys.argv) > 4 else []
        lid = add_lesson(context, lesson, tags=tags)
        print(f"Added: {lid}")
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: lesson_manager.py search <query>")
            sys.exit(1)
        for l in search_lessons(sys.argv[2]):
            print(f"[{l['id']}] {l['lesson'][:80]}")
    elif cmd == "get":
        if len(sys.argv) < 3:
            print("Usage: lesson_manager.py get <lesson_id>")
            sys.exit(1)
        print(json.dumps(get_lesson(sys.argv[2]), indent=2))
