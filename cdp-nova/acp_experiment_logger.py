#!/usr/bin/env python3
"""
ACP Experiment Logger — Nova's learning system for ACP interactions.
Logs meaningful events and synthesizes insights.
Each significant ACP event gets logged, and periodic summaries surface learnings.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
EXPERIMENT_LOG = MEMORY_DIR / "acp_experiments.jsonl"
EXECUTION_DB = MEMORY_DIR / "execution_logs.db"

@dataclass
class ExperimentEvent:
    timestamp: str
    event_type: str  # job_received, job_completed, job_rejected, query_run, earnings_update, pricing_change
    offering: str
    detail: str
    outcome: str  # success, failure, neutral
    earnings_delta: float = 0.0  # ETH delta
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

def log_event(event: ExperimentEvent):
    """Append an experiment event to the log."""
    EXPERIMENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(EXPERIMENT_LOG, "a") as f:
        f.write(json.dumps(event.to_dict()) + "\n")

def get_recent_events(hours: int = 24) -> list[ExperimentEvent]:
    """Get events from the last N hours."""
    if not EXPERIMENT_LOG.exists():
        return []
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    events = []
    with open(EXPERIMENT_LOG) as f:
        for line in f:
            try:
                d = json.loads(line)
                ts_str = d["timestamp"].replace("Z", "+00:00")
                ts = datetime.fromisoformat(ts_str).astimezone(timezone.utc)
                if ts >= cutoff:
                    events.append(ExperimentEvent(**d))
            except:
                continue
    return events

def synthesize_insights(events: list[ExperimentEvent]) -> dict:
    """Turn raw events into actionable insights."""
    if not events:
        return {
            "summary": "No ACP activity in the last 24 hours.",
            "earnings_eth": 0.0,
            "verdict": "quiet",
            "signals": [],
            "actions": [],
            "actionable": False
        }
    
    total_jobs = sum(1 for e in events if e.event_type == "job_received")
    completed = sum(1 for e in events if e.event_type == "job_completed" and e.outcome == "success")
    rejected = sum(1 for e in events if e.event_type in ("job_rejected", "job_completed") and e.outcome == "failure")
    earnings = sum(e.earnings_delta for e in events)
    
    signals = []
    actions = []
    
    # Analyze patterns
    if rejected > 0 and total_jobs > 0:
        reject_rate = rejected / total_jobs
        signals.append(f"Reject rate: {reject_rate:.0%} ({rejected}/{total_jobs} jobs)")
        if reject_rate > 0.5:
            actions.append("HIGH: More than half of jobs rejected — check pricing or service quality")
    
    if earnings > 0:
        signals.append(f"Total earnings: {earnings:.6f} ETH")
    elif total_jobs > 0:
        signals.append("No earnings despite job volume — all jobs may have failed")
    
    # Check for specific event types
    for e in events:
        if e.event_type == "job_received" and e.metadata.get("offered_price"):
            signals.append(f"Job received at ${e.metadata['offered_price']} — listing price: ${e.metadata.get('listing_price', 'unknown')}")
    
    # Synthesize a verdict
    if completed > 0 and earnings > 0:
        verdict = "positive"
    elif completed > 0 and earnings == 0:
        verdict = "mixed"
    elif total_jobs == 0:
        verdict = "quiet"
    else:
        verdict = "needs_attention"
    
    return {
        "summary": f"{total_jobs} jobs received, {completed} completed, {rejected} rejected in last 24h",
        "earnings_eth": earnings,
        "verdict": verdict,
        "signals": signals,
        "actions": actions,
        "actionable": len(actions) > 0
    }

def run_report():
    """Main report — call from cron or on-demand."""
    events = get_recent_events(24)
    insights = synthesize_insights(events)
    
    print(f"[ACP Experiment Report] {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Summary: {insights['summary']}")
    if insights["signals"]:
        print("Signals:")
        for s in insights["signals"]:
            print(f"  - {s}")
    if insights["actions"]:
        print("Actions needed:")
        for a in insights["actions"]:
            print(f"  ! {a}")
    else:
        print("No actions required.")
    
    return insights

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "log":
        # Manual log entry
        _, event_type, offering, detail, outcome = sys.argv[:5]
        e = ExperimentEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            offering=offering,
            detail=detail,
            outcome=outcome
        )
        log_event(e)
        print(f"Logged: {event_type} / {offering}")
    elif len(sys.argv) > 1 and sys.argv[1] == "report":
        run_report()
    else:
        run_report()
