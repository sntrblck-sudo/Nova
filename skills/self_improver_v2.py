#!/usr/bin/env python3
"""
Nova Self-Improver v2
=====================
Lesson-aware, pattern-detecting self-improvement system.

Runs:
1. Parse session log (or use today's cron context)
2. Extract new lessons + update existing ones
3. Run pattern sentinel (detect stuck patterns)
4. Write daily log
5. Optionally meta-improve (patch own source)
6. Surface to Sen only if action needed

Usage:
  python3 self_improver_v2.py run [--session-log "<text>" [--meta]]
  python3 self_improver_v2.py brief   # print pre-session brief
  python3 self_improver_v2.py status  # lesson/sentinel summary
"""

import hashlib
import json
import os
import re
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Ensure skills dir is on path
sys.path.insert(0, str(Path(__file__).parent))

from lesson_manager import (
    add_lesson, get_lesson, update_lesson, get_all_lessons,
    log_application, resolve_application, get_top_lessons, get_summary as lesson_summary
)
from pattern_sentinel import run_sentinel, print_report as print_sentinel
from pre_session_brief import build_brief, format_brief

WORKSPACE = Path("/home/sntrblck/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
LESSONS_DIR = MEMORY_DIR / "lessons"
DAILY_LOGS_DIR = MEMORY_DIR / "daily_logs"
SELF_PATH = Path(__file__).resolve()

DAILY_LOGS_DIR.mkdir(parents=True, exist_ok=True)
LESSONS_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")


def _ollama(prompt: str, system: str = "") -> str:
    """Call local Ollama for structured extraction."""
    import json
    import urllib.request

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OLLAMA_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except Exception as e:
        return json.dumps({"error": str(e)})


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response (looks for ```json blocks first)."""
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


# ─── Core Analysis ────────────────────────────────────────────────────────────

def reflect_on_session(session_log: str) -> dict:
    """
    Analyze a session log and extract:
    - New lessons
    - Updates to existing lessons (outcomes from application)
    - Session summary
    - Failure notes worth logging
    """
    system = (
        "You are Nova's self-improvement engine. "
        "Analyze the session log and extract structured lessons. "
        "Respond ONLY with valid JSON, no prose, no markdown fences. "
        "Fields: new_lessons[], lesson_updates[], session_summary, failure_notes[]"
    )
    prompt = f"""
Session log:
{session_log}

Extract lessons in this exact JSON format:
{{
 "new_lessons": [
  {{
   "context": "brief description of what triggered this lesson",
   "lesson": "what Nova learned or should do differently",
   "applied": "what action was taken or will be taken",
   "tags": ["#tag1", "#tag2"]
  }}
 ],
 "lesson_updates": [
  {{
   "id": "lesson_xxx",
   "outcome": "what happened when this lesson was applied",
   "improved": true
  }}
 ],
 "session_summary": "one sentence summary of the session",
 "failure_notes": ["any recurring failure worth logging as a stuck pattern"]
}}
"""
    raw = _ollama(prompt, system)
    result = _extract_json(raw)
    if "error" in result:
        return {"new_lessons": [], "lesson_updates": [], "session_summary": "Ollama unavailable", "failure_notes": []}
    return result


def apply_reflection(reflection: dict, today: str):
    """
    Persist new lessons and update existing ones based on reflection.
    Returns counts.
    """
    new_count = 0
    update_count = 0

    for new in reflection.get("new_lessons", []):
        if new.get("lesson"):
            add_lesson(
                context=new.get("context", ""),
                lesson=new.get("lesson", ""),
                applied=new.get("applied", ""),
                tags=new.get("tags", [])
            )
            new_count += 1

    for upd in reflection.get("lesson_updates", []):
        lid = upd.get("id")
        outcome = upd.get("outcome", "")
        improved = upd.get("improved", False)
        if lid:
            update_lesson(lid, outcome=outcome, improved=improved)
            log_id = log_application(
                lesson_id=lid,
                session_date=today,
                applied_context=outcome,
                outcome=outcome
            )
            resolve_application(log_id, outcome, improved)
            update_count += 1

    return new_count, update_count


def write_daily_log(today: str, reflection: dict, sentinel_result: dict):
    """Append structured entries to today's daily log."""
    log_path = DAILY_LOGS_DIR / f"{today}.jsonl"
    entries = []

    summary = reflection.get("session_summary", "")
    if summary:
        entries.append({"type": "summary", "note": summary, "ts": datetime.utcnow().isoformat()})

    for failure in reflection.get("failure_notes", []):
        entries.append({"type": "failure_note", "issue": failure, "ts": datetime.utcnow().isoformat()})

    for pattern in sentinel_result.get("stuck_patterns", []):
        entries.append({
            "type": "stuck_pattern",
            "issue": pattern.get("issue", ""),
            "occurrences": pattern.get("occurrences", 0),
            "category": pattern.get("category", ""),
            "urgency": pattern.get("urgency", ""),
            "ts": datetime.utcnow().isoformat()
        })

    if not entries:
        entries.append({"type": "no_significant_events", "ts": datetime.utcnow().isoformat()})

    with open(log_path, "a") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def write_sentinel_result(result: dict):
    """Write latest sentinel result for pre_session_brief to read."""
    sentinel_path = MEMORY_DIR / "sentinel_latest.json"
    sentinel_path.write_text(json.dumps(result, indent=2))


# ─── Meta-Improvement ─────────────────────────────────────────────────────────

def meta_self_improve(session_log: str) -> dict:
    """
    Nova reviews her own self-improver source code and proposes a patch.
    Patches are minimal, targeted, and auditted.
    """
    if OLLAMA_MODEL == "mistral" and "localhost" in OLLAMA_URL:
        # Ollama may not be running — skip meta to avoid noise
        return {"patched": False, "reason": "Ollama not available for meta-analysis"}

    current_code = SELF_PATH.read_text()
    before_hash = hashlib.sha256(current_code.encode()).hexdigest()[:12]

    system = (
        "You are Nova's meta-improvement engine. "
        "Review the self-improver source code and session log. "
        "Propose ONLY minimal, targeted patches. "
        "Respond in JSON: patch_needed (bool), reason (str), "
        "old_str (exact string to find), new_str (exact replacement). "
        "If no patch needed, return patch_needed: false only."
    )
    prompt = f"""
Self-improver source ({len(current_code)} chars):
```python
{current_code[:5000]}
```

Session log excerpt:
{session_log[:1000]}

Is there a clear, minimal improvement to make to the self-improver itself?
"""
    raw = _ollama(prompt, system)
    proposal = _extract_json(raw)

    if not proposal.get("patch_needed"):
        return {"patched": False, "reason": proposal.get("reason", "No patch needed")}

    old_str = proposal.get("old_str", "")
    new_str = proposal.get("new_str", "")

    if not old_str or old_str not in current_code:
        return {"patched": False, "reason": "Proposed patch string not found in source — skipped safely"}

    patched_code = current_code.replace(old_str, new_str, 1)
    SELF_PATH.write_text(patched_code)
    after_hash = hashlib.sha256(patched_code.encode()).hexdigest()[:12]

    audit = {
        "ts": datetime.utcnow().isoformat(),
        "before_hash": before_hash,
        "after_hash": after_hash,
        "reason": proposal.get("reason", ""),
        "old_str_preview": old_str[:80],
        "new_str_preview": new_str[:80],
    }
    audit_path = MEMORY_DIR / "self_improver_audit.jsonl"
    with open(audit_path, "a") as f:
        f.write(json.dumps(audit) + "\n")

    return {"patched": True, "audit": audit}


# ─── Surface Decision ─────────────────────────────────────────────────────────

def should_surface(result: dict) -> tuple:
    """
    Decide if this self-improver run needs Sen's attention.
    Returns (surface: bool, reason: str, summary: str)
    """
    reasons = []

    if result.get("stuck_count", 0) > 0:
        high_urgency = [p for p in result.get("stuck_patterns", []) if p.get("urgency") == "high"]
        if high_urgency:
            reasons.append(f"{len(high_urgency)} high-urgency stuck pattern(s)")
        else:
            reasons.append(f"{result['stuck_count']} stuck pattern(s)")

    if result.get("new_lessons", 0) > 0:
        reasons.append(f"{result['new_lessons']} new lesson(s)")

    if result.get("meta_patched"):
        reasons.append("Self-improver patched its own source")

    if result.get("error"):
        reasons.append(f"Error: {result['error']}")

    if not reasons:
        return False, "", "All nominal — no action needed"

    summary = "; ".join(reasons)
    # Surface for: stuck patterns, new lessons, patches
    surface = result.get("stuck_count", 0) > 0 or result.get("new_lessons", 0) > 2 or result.get("meta_patched", False)
    return surface, summary, summary


def write_surface_alert(result: dict, surface_reason: str):
    """Write alert to file for pickup by health check or Sen review."""
    lines = [
        "# Self-Improver Alert\n",
        f"**Date:** {result.get('date', datetime.utcnow().strftime('%Y-%m-%d'))}\n",
        f"**Reason:** {surface_reason}\n\n",
        "## Summary\n",
        f"- New lessons added: {result.get('new_lessons', 0)}\n",
        f"- Lesson updates: {result.get('lesson_updates', 0)}\n",
        f"- Stuck patterns: {result.get('stuck_count', 0)}\n",
        f"- Meta-patched: {result.get('meta_patched', False)}\n",
    ]

    if result.get("stuck_patterns"):
        lines.append("\n## Stuck Patterns\n")
        for p in result["stuck_patterns"]:
            lines.append(f"- **[{p['category']}]** {p['issue']}")
            lines.append(f"  → {p['recommendation']}\n")

    if result.get("meta_patched"):
        audit = result.get("meta_audit", {})
        lines.append(f"\n## Self-Patch\n")
        lines.append(f"- Before hash: `{audit.get('before_hash', '?')}`\n")
        lines.append(f"- After hash: `{audit.get('after_hash', '?')}`\n")
        lines.append(f"- Reason: {audit.get('reason', '?')}\n")

    alert_path = MEMORY_DIR / "self_improver_alert.md"
    Path(alert_path).write_text("".join(lines))


# ─── Main Run ─────────────────────────────────────────────────────────────────

def run(session_log: str = "", run_meta: bool = False) -> dict:
    """
    Full self-improver run. Returns result dict with:
    date, new_lessons, lesson_updates, stuck_patterns, meta, should_surface
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")

    result = {
        "date": today,
        "new_lessons": 0,
        "lesson_updates": 0,
        "stuck_count": 0,
        "stuck_patterns": [],
        "improving_patterns": [],
        "meta_patched": False,
        "meta_audit": {},
        "surface": False,
        "surface_reason": "",
    }

    # 1. Analyze session
    if session_log:
        reflection = reflect_on_session(session_log)
        new_count, update_count = apply_reflection(reflection, today)
        write_daily_log(today, reflection, {"stuck_patterns": []})
        result["new_lessons"] = new_count
        result["lesson_updates"] = update_count
    else:
        reflection = {"session_summary": "", "failure_notes": [], "new_lessons": []}

    # 2. Run pattern sentinel
    sentinel = run_sentinel(days=7)
    write_sentinel_result(sentinel)
    result["stuck_count"] = sentinel.get("stuck_count", 0)
    result["stuck_patterns"] = sentinel.get("stuck_patterns", [])
    result["improving_patterns"] = sentinel.get("improving_patterns", [])

    # 3. Write daily log with sentinel results too
    write_daily_log(today, reflection, sentinel)

    # 4. Meta-improvement (optional)
    if run_meta and session_log:
        meta = meta_self_improve(session_log)
        result["meta_patched"] = meta.get("patched", False)
        result["meta_audit"] = meta.get("audit", {})
        result["meta_reason"] = meta.get("reason", "")

    # 5. Decide to surface
    surface, reason, summary = should_surface(result)
    result["surface"] = surface
    result["surface_reason"] = reason

    if surface:
        write_surface_alert(result, reason)

    return result


# ─── CLI Commands ──────────────────────────────────────────────────────────────

def cmd_run(args):
    session_log = ""
    run_meta = "--meta" in args

    if "--session-log" in args:
        idx = args.index("--session-log")
        if idx + 1 < len(args):
            session_log = " ".join(args[idx + 1:])

    if not session_log and not sys.stdin.isatty():
        session_log = sys.stdin.read()

    result = run(session_log, run_meta=run_meta)

    print(json.dumps(result, indent=2))

    if result["surface"]:
        print(f"\n⚠️ SURFACED: {result['surface_reason']}")
    else:
        print("\n✅ Silent — all nominal.")

    return result


def cmd_brief(args):
    brief = build_brief()
    print(format_brief(brief))


def cmd_status(args):
    print("\n=== Lesson Library ===")
    summary = lesson_summary()
    print(json.dumps(summary, indent=2))

    print("\n=== Pattern Sentinel ===")
    result = run_sentinel()
    print_sentinel(result)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    args = sys.argv[2:]

    if cmd == "run":
        cmd_run(args)
    elif cmd == "brief":
        cmd_brief(args)
    elif cmd == "status":
        cmd_status(args)
    elif cmd == "lessons":
        for l in get_all_lessons():
            print(f"[{l['id']}] conf={l['confidence']:.2f} tags={l['tags']}")
            print(f"  context: {l['context'][:80]}")
            print(f"  lesson:  {l['lesson'][:80]}\n")
    else:
        print(f"Usage: {sys.argv[0]} [run|brief|status|lessons]")
        print("  run [--session-log '<text>'] [--meta]")
        print("  brief   # print pre-session brief")
        print("  status  # lesson + sentinel summary")
        print("  lessons # list all lessons")
