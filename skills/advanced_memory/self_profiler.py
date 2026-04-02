#!/usr/bin/env python3
"""
Self-Profiler — Updates Nova's self-profile based on experience.
Integrates with execution_logger, incidents.log, task_marker, and loop_detector.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
PROFILE_FILE = Path("/home/sntrblck/.openclaw/workspace/skills/advanced_memory/self_profile.json")
EXECUTION_DB = MEMORY_DIR / "execution_logs.db"
INCIDENTS_FILE = MEMORY_DIR / "incidents.log"
LOOP_FILE = MEMORY_DIR / "loop_log.json"
TASKS_FILE = MEMORY_DIR / "task_markers.json"

def load_profile():
    if PROFILE_FILE.exists():
        with open(PROFILE_FILE) as f:
            return json.load(f)
    return {"capabilities": [], "failure_patterns": [], "strengths": [], "debilitation": [], "meta": {}}

def save_profile(profile):
    with open(PROFILE_FILE, 'w') as f:
        json.dump(profile, f, indent=2)

def get_capability(skill):
    """Get capability entry by skill name."""
    profile = load_profile()
    for cap in profile.get("capabilities", []):
        if cap.get("skill") == skill:
            return cap
    return None

def update_capability(skill, success, evidence=None):
    """Update capability based on success or failure."""
    profile = load_profile()
    caps = profile.get("capabilities", [])
    
    # Find existing
    found = None
    for cap in caps:
        if cap.get("skill") == skill:
            found = cap
            break
    
    if found:
        # Update confidence based on outcome
        delta = 0.05 if success else -0.1
        found["confidence"] = max(0.1, min(0.99, found["confidence"] + delta))
        found["last_updated"] = datetime.now().isoformat()
        if evidence and success:
            found["evidence"].append(evidence)
            found["examples"] = list(set(found.get("examples", []) + [evidence]))
    else:
        # Create new
        caps.append({
            "skill": skill,
            "confidence": 0.5 if success else 0.3,
            "evidence": [evidence] if evidence else [],
            "examples": [evidence] if evidence else [],
            "last_updated": datetime.now().isoformat()
        })
    
    profile["capabilities"] = caps
    save_profile(profile)

def record_failure(failure_type, conditions):
    """Record a failure pattern."""
    profile = load_profile()
    failures = profile.get("failure_patterns", [])
    
    # Check if this pattern exists
    found = None
    for f in failures:
        if f.get("type") == failure_type:
            found = f
            break
    
    if found:
        found["frequency"] = increment_frequency(found.get("frequency", "rare"))
        found["last_occurrence"] = datetime.now().isoformat()
    else:
        failures.append({
            "type": failure_type,
            "conditions": conditions,
            "frequency": "occasional",
            "last_occurrence": datetime.now().isoformat()
        })
    
    profile["failure_patterns"] = failures
    save_profile(profile)

def increment_frequency(current):
    """Increment frequency counter."""
    order = ["rare", "occasional", "frequent", "chronic"]
    if current in order:
        idx = order.index(current)
        return order[min(idx + 1, len(order) - 1)]
    return "occasional"

def infer_capability_from_task(task):
    """Infer which capability a task exercises."""
    task_lower = task.lower()
    
    if "build" in task_lower or "deploy" in task_lower or "create" in task_lower:
        return "system_building"
    if "execute" in task_lower or "tx" in task_lower or "send" in task_lower:
        return "autonomous_execution"
    if "research" in task_lower or "synthesiz" in task_lower or "analyz" in task_lower:
        return "research_synthesis"
    if "philosoph" in task_lower or "identity" in task_lower or "think" in task_lower:
        return "philosophical_reasoning"
    if "write" in task_lower or "edit" in task_lower or "document" in task_lower:
        return "writing"
    if "debug" in task_lower or "fix" in task_lower or "error" in task_lower:
        return "debugging"
    
    return "general"

def analyze_execution_logs():
    """Analyze recent execution logs for patterns."""
    if not EXECUTION_DB.exists():
        return
    
    profile = load_profile()
    conn = sqlite3.connect(str(EXECUTION_DB))
    
    # Get recent events
    cursor = conn.execute("""
        SELECT event_type, task, outcome, timestamp
        FROM execution_logs
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    
    recent_events = cursor.fetchall()
    conn.close()
    
    success_count = sum(1 for e in recent_events if e[2] == "success")
    failure_count = sum(1 for e in recent_events if e[2] == "failure")
    
    # Update meta
    profile["meta"]["total_events_analyzed"] = len(recent_events)
    profile["meta"]["recent_success_rate"] = success_count / len(recent_events) if recent_events else 0
    
    # Infer capabilities from successful tasks
    for event in recent_events[:10]:
        event_type, task, outcome, _ = event
        if outcome == "success":
            cap = infer_capability_from_task(task)
            update_capability(cap, True, task[:50])
    
    save_profile(profile)
    return {"success": success_count, "failures": failure_count}

def analyze_incidents():
    """Analyze incidents for failure patterns."""
    if not INCIDENTS_FILE.exists():
        return []
    
    with open(INCIDENTS_FILE) as f:
        incidents = f.readlines()
    
    patterns = []
    for inc in incidents[-10:]:
        inc_lower = inc.lower()
        if "traceback" in inc_lower or "error" in inc_lower:
            patterns.append({"type": "code_error", "raw": inc[:100]})
        elif "timeout" in inc_lower:
            patterns.append({"type": "timeout", "raw": inc[:100]})
        elif "permission" in inc_lower or "denied" in inc_lower:
            patterns.append({"type": "permission_error", "raw": inc[:100]})
    
    for p in patterns:
        record_failure(p["type"], [p["raw"]])
    
    return patterns

def analyze_loops():
    """Analyze recent loops."""
    if not LOOP_FILE.exists():
        return []
    
    with open(LOOP_FILE) as f:
        loops = json.load(f)
    
    for loop in loops[-5:]:
        sig = loop.get("loops", [{}])[0].get("signature", "") if loop.get("loops") else ""
        if sig:
            record_failure("repetitive_actions", [sig[:80]])
    
    return loops

def run_full_analysis():
    """Run full self-analysis."""
    profile = load_profile()
    
    results = {
        "execution_analysis": analyze_execution_logs(),
        "incident_analysis": analyze_incidents(),
        "loop_analysis": analyze_loops()
    }
    
    # Update meta
    profile["meta"]["last_full_review"] = datetime.now().isoformat()
    profile["meta"]["profile_confidence"] = min(0.9, profile["meta"].get("profile_confidence", 0.5) + 0.05)
    save_profile(profile)
    
    return results

def update_from_task(task_id, outcome):
    """Update profile based on task completion."""
    profile = load_profile()
    
    # Infer capability
    cap = infer_capability_from_task(task_id)
    success = outcome in ["success", "achieved"]
    
    update_capability(cap, success, f"Task: {task_id[:30]}")
    
    if not success:
        record_failure("task_failure", [f"Task {task_id} {outcome}"])
    
    profile["meta"]["last_task_update"] = datetime.now().isoformat()
    save_profile(profile)

def get_self_assessment():
    """Get current self-assessment summary."""
    profile = load_profile()
    
    caps = profile.get("capabilities", [])
    strengths = profile.get("strengths", [])
    debils = profile.get("debilitation", [])
    
    # Top capabilities by confidence
    top_caps = sorted(caps, key=lambda x: x.get("confidence", 0), reverse=True)[:3]
    
    return {
        "top_strengths": [c["skill"] for c in top_caps],
        "weakest_areas": [c["skill"] for c in sorted(caps, key=lambda x: x.get("confidence", 1))[:2]],
        "active_failure_patterns": len(profile.get("failure_patterns", [])),
        "profile_confidence": profile.get("meta", {}).get("profile_confidence", 0),
        "ready_for_new_task": len([c for c in caps if c.get("confidence", 0) > 0.6]) >= 3
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: self_profiler.py <command>")
        print("Commands: update-capability, record-failure, analyze, assessment")
    
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "help"
    
    if cmd == "update-capability" and len(sys.argv) >= 4:
        update_capability(sys.argv[2], sys.argv[3].lower() == "true", sys.argv[4] if len(sys.argv) > 4 else None)
        print(f"Capability {sys.argv[2]} updated")
    
    elif cmd == "record-failure" and len(sys.argv) >= 3:
        record_failure(sys.argv[2], [sys.argv[3]] if len(sys.argv) > 3 else [])
        print(f"Failure {sys.argv[2]} recorded")
    
    elif cmd == "analyze":
        results = run_full_analysis()
        print(json.dumps(results, indent=2))
    
    elif cmd == "assessment":
        print(json.dumps(get_self_assessment(), indent=2))
    
    elif cmd == "show":
        print(json.dumps(load_profile(), indent=2))