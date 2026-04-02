#!/usr/bin/env python3
"""
Signal Detection System — Detect anomalies, trends, threshold crossings, patterns.
Stores signal history and identifies recurring signals.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
SIGNALS_FILE = MEMORY_DIR / "signals.json"
PATTERNS_FILE = MEMORY_DIR / "patterns.json"

# Signal classes
SIGNAL_CLASSES = {
    "operational": "System health, tool failures, queue pressure, degraded recovery",
    "strategic": "Market/tech shifts, emerging topics, ecosystem changes",  
    "human": "Operator preferences, recurring frustrations, stable interests",
    "identity": "What Nova consistently finds valuable, trusted formats"
}

# Signal severity
SEVERITY_LEVELS = ["info", "watch", "concern", "warning", "critical"]

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def detect_signal(signal_type, signal_class, description, severity, metadata=None):
    """
    Record a detected signal.
    
    signal_type: what kind of signal (e.g., "threshold_crossed", "anomaly", "trend")
    signal_class: operational | strategic | human | identity
    description: what happened
    severity: info | watch | concern | warning | critical
    metadata: additional context
    """
    signals = load_json(SIGNALS_FILE)
    if "signals" not in signals:
        signals["signals"] = []
    
    signal_id = f"sig_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{signal_type[:10]}"
    
    signal = {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "signal_class": signal_class,
        "description": description,
        "severity": severity,
        "metadata": metadata or {},
        "detected_at": datetime.now().isoformat(),
        "repeat_count": check_repeat(signal_type, description),
        "related_signals": find_related(signal_type)
    }
    
    signals["signals"].append(signal)
    
    # Keep last 200 signals
    signals["signals"] = signals["signals"][-200:]
    
    # Update patterns
    update_patterns(signal)
    
    save_json(SIGNALS_FILE, signals)
    
    return signal

def check_repeat(signal_type, description):
    """Check if a similar signal has been seen before."""
    signals = load_json(SIGNALS_FILE)
    count = 0
    
    for sig in signals.get("signals", [])[-20:]:
        if sig["signal_type"] == signal_type:
            count += 1
    
    return count

def find_related(signal_type):
    """Find signals of the same type seen recently."""
    signals = load_json(SIGNALS_FILE)
    related = []
    
    for sig in signals.get("signals", [])[-50:]:
        if sig["signal_type"] == signal_type and sig["signal_id"] not in related:
            related.append(sig["signal_id"])
    
    return related[-5:]  # Last 5 related

def update_patterns(signal):
    """Update pattern tracking when a signal is detected."""
    patterns = load_json(PATTERNS_FILE)
    if "patterns" not in patterns:
        patterns["patterns"] = []
    
    # Check if this pattern exists
    pattern_found = False
    for pat in patterns["patterns"]:
        if pat["signal_type"] == signal["signal_type"]:
            pat["count"] += 1
            pat["last_seen"] = signal["detected_at"]
            pat["recent_signals"].append(signal["signal_id"])
            pat["recent_signals"] = pat["recent_signals"][-10:]
            
            # Update severity if higher
            if SEVERITY_LEVELS.index(signal["severity"]) > SEVERITY_LEVELS.index(pat.get("max_severity", "info")):
                pat["max_severity"] = signal["severity"]
            
            pattern_found = True
            break
    
    if not pattern_found:
        patterns["patterns"].append({
            "signal_type": signal["signal_type"],
            "count": 1,
            "first_seen": signal["detected_at"],
            "last_seen": signal["detected_at"],
            "max_severity": signal["severity"],
            "recent_signals": [signal["signal_id"]]
        })
    
    # Keep only patterns seen in last 30 days
    cutoff = datetime.now() - timedelta(days=30)
    patterns["patterns"] = [
        p for p in patterns["patterns"]
        if datetime.fromisoformat(p["last_seen"]) > cutoff
    ]
    
    save_json(PATTERNS_FILE, patterns)

def get_signals_by_class(signal_class, limit=20):
    """Get recent signals by class."""
    signals = load_json(SIGNALS_FILE)
    filtered = [
        s for s in signals.get("signals", [])
        if s["signal_class"] == signal_class
    ]
    return filtered[-limit:]

def get_signals_by_severity(severity, limit=20):
    """Get recent signals by severity."""
    signals = load_json(SIGNALS_FILE)
    filtered = [
        s for s in signals.get("signals", [])
        if s["severity"] in SEVERITY_LEVELS[SEVERITY_LEVELS.index(severity):]
    ]
    return filtered[-limit:]

def get_recurring_signals(min_count=3):
    """Get signals that have appeared multiple times."""
    patterns = load_json(PATTERNS_FILE)
    return [
        p for p in patterns.get("patterns", [])
        if p["count"] >= min_count
    ]

def get_anomalies():
    """Get high-severity or recurring signals that might be anomalies."""
    signals = load_json(SIGNALS_FILE).get("signals", [])
    patterns = load_json(PATTERNS_FILE).get("patterns", [])
    
    anomalies = []
    
    # High severity signals
    for sig in signals[-50:]:
        if sig["severity"] in ["warning", "critical"]:
            anomalies.append({
                "type": "high_severity",
                "signal": sig
            })
    
    # Recurring patterns
    for pat in patterns:
        if pat["count"] >= 3:
            anomalies.append({
                "type": "recurring_pattern",
                "pattern": pat
            })
    
    return anomalies

def get_watchlist():
    """Get items that should be watched/monitored."""
    patterns = load_json(PATTERNS_FILE).get("patterns", [])
    signals = load_json(SIGNALS_FILE).get("signals", [])
    
    watchlist = []
    
    # Recurring patterns to watch
    for pat in patterns:
        if pat["count"] >= 2:
            watchlist.append({
                "item": pat["signal_type"],
                "reason": f"seen {pat['count']} times",
                "last_seen": pat["last_seen"]
            })
    
    # Recent watch-level signals
    for sig in signals[-20:]:
        if sig["severity"] == "watch":
            watchlist.append({
                "item": sig["signal_type"],
                "reason": sig["description"][:50],
                "last_seen": sig["detected_at"]
            })
    
    return watchlist

def get_stats():
    """Get signal detection statistics."""
    signals = load_json(SIGNALS_FILE).get("signals", [])
    patterns = load_json(PATTERNS_FILE).get("patterns", [])
    
    by_class = Counter(s["signal_class"] for s in signals)
    by_severity = Counter(s["severity"] for s in signals)
    
    return {
        "total_signals": len(signals),
        "total_patterns": len(patterns),
        "recurring_count": len([p for p in patterns if p["count"] >= 3]),
        "by_class": dict(by_class),
        "by_severity": dict(by_severity),
        "anomaly_count": len(get_anomalies()),
        "watchlist_count": len(get_watchlist())
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: signals.py <command> [args]")
        print("Commands: detect, by-class, by-severity, recurring, anomalies, watchlist, stats")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "detect" and len(sys.argv) >= 5:
        sig_type = sys.argv[2]
        sig_class = sys.argv[3]
        severity = sys.argv[4]
        desc = sys.argv[5] if len(sys.argv) > 5 else ""
        result = detect_signal(sig_type, sig_class, desc, severity)
        print(f"Signal detected: {result['signal_id']}")
        print(json.dumps(result, indent=2))
    
    elif cmd == "by-class" and len(sys.argv) >= 3:
        signals = get_signals_by_class(sys.argv[2])
        print(f"Signals of class '{sys.argv[2]}': {len(signals)}")
        for s in signals[-5:]:
            print(f"  [{s['severity']}] {s['description'][:60]}")
    
    elif cmd == "by-severity" and len(sys.argv) >= 3:
        signals = get_signals_by_severity(sys.argv[2])
        print(f"Signals of severity '{sys.argv[2]}': {len(signals)}")
        for s in signals[-5:]:
            print(f"  [{s['signal_class']}] {s['description'][:60]}")
    
    elif cmd == "recurring":
        patterns = get_recurring_signals()
        print(f"Recurring patterns (3+): {len(patterns)}")
        for p in patterns:
            print(f"  {p['signal_type']}: {p['count']} times")
    
    elif cmd == "anomalies":
        anomalies = get_anomalies()
        print(f"Anomalies: {len(anomalies)}")
        for a in anomalies[:5]:
            print(f"  [{a['type']}] {a.get('signal', {}).get('description', a.get('pattern', {}).get('signal_type', ''))[:50]}")
    
    elif cmd == "watchlist":
        watchlist = get_watchlist()
        print(f"Watchlist items: {len(watchlist)}")
        for w in watchlist[:10]:
            print(f"  - {w['item']}: {w['reason']}")
    
    elif cmd == "stats":
        print(json.dumps(get_stats(), indent=2))
    
    elif cmd == "test":
        # Test detection
        sig = detect_signal(
            "threshold_crossed",
            "operational",
            "Wallet balance below 0.001 ETH",
            "watch",
            {"balance": 0.0009}
        )
        print(f"Test signal: {sig['signal_id']}, repeats: {sig['repeat_count']}")
        
        # Detect another similar
        sig2 = detect_signal(
            "threshold_crossed",
            "operational",
            "Wallet balance still low",
            "concern",
            {"balance": 0.0008}
        )
        print(f"Repeat signal: {sig2['repeat_count']} repeats")
        
        anomalies = get_anomalies()
        print(f"Anomalies: {len(anomalies)}")
    
    else:
        print("Invalid command")