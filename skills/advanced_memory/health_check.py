#!/usr/bin/env python3
"""
Nova Health Check - Component B
Verifies key services and logs incidents.
Run periodically (e.g., every few hours) via heartbeat.
"""

import json
import subprocess
import os
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
HEALTH_STATUS = LOG_DIR / "health_status.json"
INCIDENTS_LOG = LOG_DIR / "incidents.log"
HEALTH_SUMMARY = LOG_DIR / "health_summary.md"

def log(msg):
    print(f"[health-check] {msg}")

def check_openclaw_status():
    """Check if openclaw gateway and core services are responding."""
    try:
        result = subprocess.run(
            ["openclaw", "status", "--json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                gateway = data.get("gateway", {})
                channels = data.get("channels", {})
                
                issues = []
                
                # Check gateway
                if gateway.get("mode") != "local" or "unreachable" in str(gateway).lower():
                    issues.append("Gateway not in local mode or unreachable")
                
                # Check Telegram - channelSummary is a list of strings like "Telegram: configured"
                channel_summary = data.get("channelSummary", [])
                telegram_ok = False
                for item in channel_summary:
                    if "Telegram" in str(item) and "configured" in str(item):
                        telegram_ok = True
                        break
                if not telegram_ok:
                    issues.append("Telegram channel not properly configured")
                
                return {"status": "ok" if not issues else "warning", "issues": issues}
            except json.JSONDecodeError:
                return {"status": "warning", "issues": ["Could not parse openclaw status JSON"]}
        else:
            return {"status": "error", "issues": [f"openclaw status failed: {result.stderr[:200]}"]}
    except subprocess.TimeoutExpired:
        return {"status": "error", "issues": ["openclaw status timed out"]}
    except Exception as e:
        return {"status": "error", "issues": [str(e)[:100]]}

def check_execution_log_failures(since_timestamp):
    """Check for new failures in execution log since given time."""
    try:
        from execution_logger import get_logs_since
        logs = get_logs_since(since_timestamp)
        failures = [l for l in logs if l[4] in ("failure", "error")]
        if failures:
            return {"has_failures": True, "count": len(failures), "examples": [f[3] for f in failures[:3]]}
        return {"has_failures": False}
    except Exception as e:
        return {"has_failures": False, "error": str(e)[:100]}

def check_files_exist():
    """Verify key files exist."""
    required = [
        "/home/sntrblck/.openclaw/workspace/memory/execution_logs.db",
        "/home/sntrblck/.openclaw/workspace/memory/state_notes.md",
        "/home/sntrblck/.openclaw/workspace/memory/continuity.log",
    ]
    missing = [f for f in required if not Path(f).exists()]
    return {"missing": missing}


def check_wallet_incoming():
    """Check for incoming payments to Nova's wallet."""
    try:
        # Import the balance checker
        result = subprocess.run(
            ["python3", "-c", """
import sys
sys.path.insert(0, '/home/sntrblck/.openclaw/workspace/cdp-nova')
from incoming_detector import check_for_incoming, load_state
result = check_for_incoming()
if result['detected']:
    print('INCOMING:' + str(result['incoming_eth']))
else:
    print('OK:' + str(result['current_balance']))
"""],
            capture_output=True, text=True, cwd="/home/sntrblck/.openclaw/workspace/cdp-nova"
        )
        output = result.stdout.strip()
        if output.startswith("INCOMING:"):
            return {"status": "incoming", "amount": float(output.split(":")[1])}
        elif output.startswith("OK:"):
            return {"status": "ok", "balance": float(output.split(":")[1])}
        return {"status": "unknown"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:100]}

def load_previous_health():
    """Load previous health status to detect repeated issues."""
    if HEALTH_STATUS.exists():
        try:
            with open(HEALTH_STATUS) as f:
                return json.load(f)
        except:
            pass
    return {}

def save_health_status(status):
    """Save current health status."""
    with open(HEALTH_STATUS, 'w') as f:
        json.dump(status, f, indent=2)

def check_staking_health():
    """Check Nova's staking position and pending rewards."""
    try:
        result = subprocess.run(
            ["python3", "/home/sntrblck/.openclaw/workspace/cdp-nova/compound.py", "check"],
            capture_output=True, text=True, timeout=60
        )
        output = result.stdout.strip()
        # Parse "SENATOR staked: X" etc
        lines = output.split("\n")
        data = {}
        for line in lines:
            if ":" in line:
                key, val = line.split(":", 1)
                data[key.strip()] = val.strip()
        
        return {
            "status": "ok",
            "senator_staked": data.get("SENATOR staked", "unknown"),
            "claws_pending": data.get("CLAWS pending", "unknown"),
            "claws_balance": data.get("CLAWS balance", "unknown"),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:100]}


def log_incident(issue_type, message, severity="warning"):
    """Log an incident to incidents.log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(INCIDENTS_LOG, 'a') as f:
        f.write(f"[{timestamp}] [{severity.upper()}] {issue_type}: {message}\n")

def suppress_spam(issue, previous_health):
    """Suppress repeated spam for known unresolved failures unless severity changed."""
    prev = previous_health.get("last_issue_type")
    if prev == issue and previous_health.get("last_severity") == "warning":
        return True  # Suppress
    return False

def run_health_check():
    log("Starting health check...")
    
    previous = load_previous_health()
    
    # Run checks
    openclaw = check_openclaw_status()
    files = check_files_exist()
    exec_log = check_execution_log_failures("2026-03-28 00:00:00")  # Since midnight
    wallet = check_wallet_incoming()
    staking = check_staking_health()

    # Run disk pruner silently (auto-prunes safe items, logs to incidents if surfacing needed)
    try:
        import disk_pruner
        prune_cfg = disk_pruner.load_config()
        if prune_cfg.get("enabled"):
            prune_results = disk_pruner.scan_workspace(prune_cfg)
            if prune_results["auto_prune"]:
                disk_pruner.do_prune(prune_results["auto_prune"], dry_run=False)
            disk = {"status": "ok", "auto_pruned": len(prune_results["auto_prune"]),
                    "surface_count": len(prune_results["surface"])}
        else:
            disk = {"status": "skipped", "reason": "disabled in config"}
    except Exception as e:
        disk = {"status": "warning", "error": str(e)[:100]}

    # Compile status
    status = {
        "timestamp": datetime.now().isoformat(),
        "openclaw": openclaw,
        "files": files,
        "execution_log": exec_log,
        "wallet": wallet,
        "staking": staking,
        "disk": disk,
    }
    
    # Determine overall health
    if openclaw["status"] == "error":
        status["overall"] = "error"
    elif openclaw["status"] == "warning" or files.get("missing") or exec_log.get("has_failures"):
        status["overall"] = "warning"
    else:
        status["overall"] = "ok"
    
    # Handle incidents
    issues = []
    if openclaw["status"] != "ok":
        for issue in openclaw["issues"]:
            if not suppress_spam(f"openclaw:{issue}", previous):
                log_incident("openclaw", issue)
                issues.append(f"openclaw: {issue}")
    
    if files.get("missing"):
        for f in files["missing"]:
            log_incident("file_missing", f, severity="error")
            issues.append(f"missing: {f}")
    
    if exec_log.get("has_failures"):
        for ex in exec_log.get("examples", []):
            log_incident("exec_failure", ex)
            issues.append(f"exec: {ex}")
    
    status["last_issue_type"] = issues[0] if issues else None
    status["last_severity"] = "error" if status["overall"] == "error" else "warning" if issues else "ok"
    
    save_health_status(status)
    
    # Write brief summary
    with open(HEALTH_SUMMARY, 'w') as f:
        f.write(f"# Health Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"Overall: **{status['overall'].upper()}**\n\n")
        if issues:
            f.write("Issues:\n")
            for issue in issues:
                f.write(f"- {issue}\n")
        else:
            f.write("No issues detected.\n")
    
    log(f"Health check complete: {status['overall']}")
    print(json.dumps(status, indent=2))
    return status

if __name__ == "__main__":
    run_health_check()
