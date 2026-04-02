#!/usr/bin/env python3
"""
Watchdog Health Check — Run via cron every 4 hours.
Checks circuit breakers, deadletter, and overall system health.
"""

import json
import sys
from pathlib import Path

# Add skills path for imports
sys.path.insert(0, str(Path(__file__).parent))

from breakers import get_all_breakers, record_failure, record_success, can_execute
from deadletter import get_stats, has_deadletter

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
HEALTH_FILE = MEMORY_DIR / "health_summary.md"

def run_watchdog():
    """Run full watchdog health check."""
    print("[watchdog] Running health check...")
    
    report = {
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        "breakers": {},
        "deadletter": {},
        "recommendations": []
    }
    
    # Check breakers
    breakers = get_all_breakers()
    for name, state in breakers.items():
        report["breakers"][name] = state["state"]
        
        # Log open breakers
        if state["state"] == "open":
            report["recommendations"].append(f"Circuit breaker OPEN: {name}")
    
    # Check deadletter
    stats = get_stats()
    report["deadletter"] = stats
    
    if stats["pending"] > 0:
        report["recommendations"].append(f"Deadletter has {stats['pending']} pending items")
    
    # Generate health report
    generate_health_file(report)
    
    # Print summary
    print(f"[watchdog] Breakers: {report['breakers']}")
    print(f"[watchdog] Deadletter: {stats['pending']} pending")
    
    if report["recommendations"]:
        print("[watchdog] ⚠️ Recommendations:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")
    else:
        print("[watchdog] ✅ All systems nominal")
    
    return report

def generate_health_file(report):
    """Write health summary to memory file."""
    import datetime
    
    breakers_status = "\n".join([
        f"- **{name}**: {state}" 
        for name, state in report["breakers"].items()
    ])
    
    recommendations = "\n".join([
        f"- {rec}" 
        for rec in report["recommendations"]
    ]) or "None"
    
    content = f"""# Health Summary

**Generated:** {report['timestamp']}
**Status:** {'⚠️ DEGRADED' if report['recommendations'] else '✅ NOMINAL'}

## Circuit Breakers
{breakers_status or "No breakers configured"}

## Deadletter Queue
- **Pending:** {report['deadletter'].get('pending', 0)}
- **Resolved:** {report['deadletter'].get('resolved', 0)}

## Recommendations
{recommendations}

## Quick Commands
```
# Check breakers
python3 skills/advanced_memory/breakers.py status

# Check deadletter  
python3 skills/advanced_memory/deadletter.py pending

# Force preflight
python3 skills/advanced_memory/preflight.py
```
"""
    
    with open(HEALTH_FILE, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    run_watchdog()