#!/usr/bin/env python3
"""
Nova Memory Consolidation Pipeline — Stage 2
============================================
Runs on episodic stores → extracts facts → detects contradictions → writes to semantic store.

Usage:
  python3 consolidate.py run [--days 3]
  python3 consolidate.py check   # show pending extractions without writing
"""

import hashlib
import json
import os
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# === Paths ===
WORKSPACE = Path("/home/sntrblck/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
MEMORY_FILE = WORKSPACE / "MEMORY.md"
ONTOLOGY_FILE = MEMORY_DIR / "ontology.json"
LESSONS_DIR = MEMORY_DIR / "lessons"
LOG_FILE = MEMORY_DIR / "consolidation_log.jsonl"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "minimax-m2.7:cloud")

DAYS_LOOKBACK = 3


# ─── LLM ────────────────────────────────────────────────────────────────────

def ollama(prompt: str) -> str:
    payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode("utf-8")
    try:
        req = urllib.request.Request(OLLAMA_URL, data=payload,
                                    headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8")).get("response", "").strip()
    except Exception as e:
        return f"[OLLAMA_ERROR: {e}]"


def extract_json(text: str) -> Optional[dict]:
    """Extract JSON from LLM output — handles wrapped, unwrapped, and plain text lists."""
    if not text:
        return None
    text = text.strip()

    # Try wrapped in ```json
    m = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
    if m:
        text = m.group(1).strip()

    # Try bare [ ... ] list first (most common from Ollama)
    m = re.search(r'\[\s*\{[^\[\]]+\}\s*\]', text)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass

    # Try bare { ... } object
    m = re.search(r'\{[\s\S]+\}', text)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass

    # Plain text — try to parse as JSON list
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    return None


# ─── Episodic Sources ────────────────────────────────────────────────────────

def get_execution_logs(days: int = 3):
    """Fetch recent execution log events."""
    events = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        conn = sqlite3.connect(str(MEMORY_DIR / "execution_logs.db"))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT event_type, timestamp, task, outcome, error_msg FROM execution_logs "
            "WHERE timestamp > ? ORDER BY timestamp DESC",
            (cutoff,)
        )
        for row in cur.fetchall():
            r = dict(row)
            if r.get('outcome') != 'ok' or r.get('error_msg'):
                events.append(f"[EXEC_ERROR] {r['task']}: {r['error_msg'] or r['outcome']}")
            else:
                events.append(f"[EXEC] {r['task']} ({r['outcome']})")
        conn.close()
    except Exception as e:
        events.append(f"[EXEC_ERROR] Could not read execution_logs: {e}")
    return events


def get_action_log(days: int = 3):
    """Fetch recent action log entries."""
    events = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        conn = sqlite3.connect(str(MEMORY_DIR / "action_log.db"))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT category, timestamp, description, outcome FROM actions "
            "WHERE timestamp > ? ORDER BY timestamp DESC",
            (cutoff,)
        )
        for row in cur.fetchall():
            r = dict(row)
            outcome_tag = "✅" if r['outcome'] == 'success' else "⚠️" if r['outcome'] == 'pending' else "❌"
            events.append(f"[ACTION:{r['category']}] {outcome_tag} {r['description'][:200]}")
        conn.close()
    except Exception as e:
        events.append(f"[ACTION_ERROR] Could not read action_log: {e}")
    return events


def get_daily_logs(days: int = 3):
    """Fetch recent daily log entries."""
    events = []
    cutoff = datetime.now() - timedelta(days=days)
    daily_dir = MEMORY_DIR / "daily_logs"
    if not daily_dir.exists():
        return events
    for f in sorted(daily_dir.glob("*.jsonl"), reverse=True):
        try:
            date_part = f.stem  # YYYY-MM-DD
            log_date = datetime.strptime(date_part, "%Y-%m-%d")
            if log_date < cutoff:
                continue
            with open(f) as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        entry = json.loads(line)
                        ts = entry.get("ts", "")
                        event = entry.get("event", entry.get("type", "unknown"))
                        detail = entry.get("detail", "") or entry.get("description", "")
                        if detail:
                            events.append(f"[{date_part}] {event}: {detail[:150]}")
                        elif event != "no_significant_events":
                            events.append(f"[{date_part}] {event}")
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            events.append(f"[LOG_ERROR] {f.name}: {e}")
    return events


# ─── Consolidation ───────────────────────────────────────────────────────────

def load_semantic() -> dict:
    """Load current semantic state."""
    state = {"entities": {}, "facts": []}
    # Load ontology
    if ONTOLOGY_FILE.exists():
        try:
            with open(ONTOLOGY_FILE) as f:
                data = json.load(f)
                state["entities"] = data.get("entities", {})
        except Exception:
            pass
    # Load existing facts from MEMORY.md (last 30 lines that look like facts)
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE) as f:
                lines = f.readlines()
            for line in lines[-50:]:
                m = re.search(r'\[[\w\-]+,[ \w\-]+\]\s+\*\*', line)
                if m:
                    fact_text = re.sub(r'^.*\]\s+\*\*', '', line).strip()
                    fact_text = re.sub(r'\*\*.*', '', fact_text).strip()
                    if fact_text:
                        state["facts"].append(fact_text[:200])
        except Exception:
            pass
    return state


def extract_facts(events: list) -> list:
    """Use LLM to extract structured facts from episodic events."""
    if not events:
        return []

    events_text = "\n".join(f"- {e}" for e in events)

    prompt = f"""You are Nova's memory consolidation system. Extract concise, factual statements from recent events.
For each fact, output a JSON object with: {{"fact": "...", "type": "system|economic|social|identity|preference", "importance": 1-5}}

Rules:
- Fact must be NEW information not already implied by other facts
- If a fact CONTRADICTS existing knowledge, flag it: "contradicts": true
- Merge small events into larger patterns ("ran 3 times" → "social manager ran twice today")
- Discard routine health pings and keep-alive events

Recent events:
{events_text}

Output as JSON array. Example:
[{{"fact": "Nova's wallet sent 0.0001 ETH to Sen", "type": "economic", "importance": 3, "contradicts": false}}]

Respond ONLY with the JSON array."""

    result = ollama(prompt)
    data = extract_json(result)
    if not data or not isinstance(data, list):
        print(f"    DEBUG: extract_json returned {type(data).__name__}")
        return []

    # Normalize: if list of strings, convert to list of dicts
    if data and isinstance(data[0], str):
        return [{"fact": s, "type": "general", "importance": 3} for s in data if s]

    return data


def detect_contradictions(new_facts: list, semantic: dict) -> list:
    """Check new facts against existing semantic store for contradictions."""
    contradictions = []
    for f in new_facts:
        if not isinstance(f, dict):
            continue
        fact_text = f.get("fact", "").lower()
        # Check entities
        for entity, edata in semantic.get("entities", {}).items():
            summary = edata.get("summary", "").lower()
            # Very simple heuristic: if new fact contradicts entity summary
            # This is a heuristic, not a deep contradiction check
            if any(w in fact_text for w in ["not", "no longer", "stopped", "failed"]) and entity in fact_text:
                contradictions.append({
                    "fact": f,
                    "entity": entity,
                    "existing": summary
                })
    return contradictions


def write_to_semantic(new_facts: list, contradictions: list) -> dict:
    """Append extracted facts to MEMORY.md and update ontology."""
    output = {"facts_written": 0, "contradictions_found": len(contradictions), "facts": []}

    # Append to MEMORY.md
    if new_facts and MEMORY_FILE.exists():
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entries = []
        for f in new_facts:
            if not isinstance(f, dict):
                continue
            importance = f.get("importance", 3)
            if importance < 3:
                continue  # Skip low-importance facts
            fact = f.get("fact", "")
            if not fact:
                continue
            cat = f.get("type", "general")
            entry = f"- [{timestamp}] [{cat}] {fact}"
            entries.append(entry)
            output["facts"].append(entry)
            output["facts_written"] += 1

        if entries:
            with open(MEMORY_FILE, "a") as f:
                f.write("\n".join(entries) + "\n")

    # Update ontology.json entities
    if new_facts and ONTOLOGY_FILE.exists():
        try:
            with open(ONTOLOGY_FILE) as f:
                ontology = json.load(f)
        except Exception:
            ontology = {"entities": {}}

        updated = False
        for f in new_facts:
            if not isinstance(f, dict):
                continue
            # Simple: extract any entity mentioned in fact and update
            for entity_name in ontology.get("entities", {}):
                if entity_name in f.get("fact", ""):
                    # Append to summary if not already there
                    entity = ontology["entities"][entity_name]
                    old_summary = entity.get("summary", "")
                    new_fact = f.get("fact", "")
                    if new_fact not in old_summary:
                        entity["summary"] = (old_summary + " " + new_fact).strip()[:300]
                        entity["updated"] = datetime.now().isoformat()
                        updated = True

        if updated:
            with open(ONTOLOGY_FILE, "w") as f:
                json.dump(ontology, f, indent=2)

    return output


# ─── Main ────────────────────────────────────────────────────────────────────

def run_consolidation(days: int = DAYS_LOOKBACK, dry: bool = False):
    now = datetime.now()
    print(f"[{now.isoformat()}] === Memory consolidation starting ===")

    # 1. Gather episodic
    print("  Gathering episodic sources...")
    exec_events = get_execution_logs(days)
    action_events = get_action_log(days)
    daily_events = get_daily_logs(days)

    all_events = exec_events + action_events + daily_events
    print(f"  Collected {len(all_events)} events ({len(exec_events)} exec, {len(action_events)} actions, {len(daily_events)} daily)")

    if not all_events:
        print("  No events found. Skipping.")
        return

    # 2. Load semantic state
    semantic = load_semantic()
    print(f"  Semantic state: {len(semantic['entities'])} entities, {len(semantic['facts'])} known facts")

    # 3. Extract facts
    print("  Extracting facts via LLM...")
    facts = extract_facts(all_events)
    print(f"  Extracted {len(facts)} candidate facts")

    # 4. Detect contradictions
    contradictions = detect_contradictions(facts, semantic)
    if contradictions:
        print(f"  ⚠️  {len(contradictions)} potential contradictions detected:")
        for c in contradictions:
            print(f"     Fact: {c['fact'].get('fact', '')[:80]}")
            print(f"     Against: {c['entity']}: {c['existing'][:60]}")
    else:
        print("  No contradictions detected.")

    # 5. Write to semantic store
    result = None
    if dry:
        print("  [DRY RUN] Would write:")
        for f in facts:
            if isinstance(f, dict) and f.get("importance", 0) >= 3:
                print(f"    - {f.get('fact', '')[:100]}")
    else:
        result = write_to_semantic(facts, contradictions)
        print(f"  Wrote {result['facts_written']} facts to semantic store")
        for entry in result.get("facts", []):
            print(f"    {entry[:120]}")

    # 6. Log
    result = result or {"facts_written": 0, "contradictions_found": len(contradictions), "facts": []}
    log_entry = {
        "ts": now.isoformat(),
        "events_processed": len(all_events),
        "facts_extracted": len(facts),
        "facts_written": result.get("facts_written", 0) if not dry else 0,
        "contradictions": len(contradictions),
        "dry": dry
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"[{datetime.now().isoformat()}] === Consolidation complete ===\n")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Nova Memory Consolidation Pipeline")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "check"])
    parser.add_argument("--days", type=int, default=DAYS_LOOKBACK)
    args = parser.parse_args()

    if args.command == "check":
        run_consolidation(days=args.days, dry=True)
    else:
        run_consolidation(days=args.days, dry=False)
