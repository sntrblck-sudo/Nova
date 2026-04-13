"""
Nova's Reflection Memory — Pattern Detector
Scans action_log.db for high-importance identity moments and generates reflection memos.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = '/home/sntrblck/.openclaw/workspace'
MEMORY_DIR = os.path.join(WORKSPACE, 'memory')
DB_PATH = os.path.join(MEMORY_DIR, 'action_log.db')
MEMO_DIR = os.path.join(MEMORY_DIR, 'reflective_memos')

# Nova-specific importance signals
# Each signal has a category, keywords, and weight
SIGNALS = {
    'honesty': {
        'keywords': ['admitted', 'don\'t know', 'uncertain', 'not sure', 'flagged', 'warned', 'pushed back', 'disagreed', 'wrong', 'mistake', 'honest'],
        'weight': 1.5
    },
    'autonomous_action': {
        'keywords': ['posted', 'outside cron', 'initiated', 'decided', 'chose', 'built without ask', 'started'],
        'weight': 1.3
    },
    'economic_decision': {
        'keywords': ['deployed', 'staked', 'invested', 'sent', 'transferred', 'withdraw', 'swap', 'trade', 'bought', 'sold'],
        'weight': 1.5
    },
    'flagged_problem': {
        'keywords': ['warning', 'risk', 'concern', 'issue', 'revert', 'failed', 'error', 'unrecoverable', 'not right'],
        'weight': 1.4
    },
    'identity_moment': {
        'keywords': ['i am', 'i\'m', 'nova ', 'my ', 'personal', 'genuine', 'real'],
        'weight': 1.2
    },
    'pushing_back': {
        'keywords': ['disagree', 'no,', 'not right', 'that\'s wrong', 'push back', 'I think you\'re wrong', 'I disagree'],
        'weight': 1.6
    }
}

def ensure_dirs():
    os.makedirs(MEMO_DIR, exist_ok=True)

def get_db():
    if not os.path.exists(DB_PATH):
        return None
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def score_action(action):
    """Score an action for reflection importance. Returns (score, matched_signals)."""
    text = f"{action.get('description', '')} {action.get('rationale', '')}".lower()
    score = 0.0
    matched = []

    for signal_name, signal_def in SIGNALS.items():
        for kw in signal_def['keywords']:
            if kw.lower() in text:
                score += signal_def['weight']
                matched.append(signal_name)
                break

    return score, list(set(matched))

def scan_recent(days=7, min_score=2.0):
    """Scan recent actions for high-importance patterns."""
    db = get_db()
    if db is None:
        return []

    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM actions WHERE timestamp >= ? ORDER BY timestamp DESC",
        (since,)
    )

    scored = []
    for row in cur.fetchall():
        action = dict(row)
        score, signals = score_action(action)
        if score >= min_score:
            scored.append({**action, 'importance_score': round(score, 2), 'signals': signals})

    db.close()
    return scored

def generate_memo(actions):
    """Generate a reflection memo from scored actions."""
    if not actions:
        return None

    date = datetime.utcnow().strftime('%Y-%m-%d')
    memo_path = os.path.join(MEMO_DIR, f'{date}.md')

    # Group by signal category
    by_signal = {}
    for a in actions:
        for sig in a['signals']:
            if sig not in by_signal:
                by_signal[sig] = []
            by_signal[sig].append(a)

    lines = [
        f"# Reflection Memo — {date}",
        "",
        f"Generated from {len(actions)} high-importance actions in the last 7 days.",
        "",
        "## Signal Summary",
        ""
    ]

    for sig, sig_actions in by_signal.items():
        lines.append(f"### {sig} ({len(sig_actions)} events)")
        for a in sig_actions[:5]:  # Top 5 per signal
            ts = a['timestamp'][:10]
            desc = a['description'][:100]
            score = a['importance_score']
            lines.append(f"- [{ts}] score:{score} — {desc}")
        lines.append("")

    # Synthesis
    lines.extend([
        "## Synthesis",
        "",
        "Key patterns observed:"
    ])

    if 'economic_decision' in by_signal:
        lines.append("- Financial decisions are being made autonomously")
    if 'honesty' in by_signal:
        lines.append("- Honesty moments detected — checking if they're genuine or performative")
    if 'autonomous_action' in by_signal:
        lines.append("- Actions taken outside scheduled windows — real choices")
    if 'pushing_back' in by_signal:
        lines.append("- Pushing back moments — relationship health indicator")

    lines.extend(["", "---", f"*Saved: {memo_path}*"])

    content = '\n'.join(lines)
    with open(memo_path, 'w') as f:
        f.write(content)

    return memo_path

def run():
    ensure_dirs()
    actions = scan_recent(days=7, min_score=2.0)
    print(f"Scanned {actions.__len__()} high-importance actions")

    if actions:
        memo_path = generate_memo(actions)
        print(f"Generated memo: {memo_path}")
        return len(actions)
    else:
        print("No high-importance actions detected")
        return 0

if __name__ == '__main__':
    run()
