"""
Nova's Reflection Memory — Pattern Scanner v2
Scans daily memory files for high-importance Nova moments.
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_DIR = '/home/sntrblck/.openclaw/workspace/memory'
MEMO_DIR = os.path.join(MEMORY_DIR, 'reflective_memos')
os.makedirs(MEMO_DIR, exist_ok=True)

# Refined signals — lower false positive rate
SIGNALS = {
    'honesty': {
        'keywords': ["i don't know", "i don't understand", "not sure", "uncertain", "admitted", "flagged", "warned", "not performing", "genuine", "honest", "that feels", "i was wrong"],
        'weight': 1.5,
        'contextual': True
    },
    'autonomous_action': {
        'keywords': ["posted", "initiated", "decided", "built without", "started working", "chose to", "outside cron", "autonomous"],
        'weight': 1.3,
        'contextual': False
    },
    'economic': {
        'keywords': ["deployed", "staked", "invested", "morpho", "sent eth", "sent usdc", "swapped", "traded", "withdraw request"],
        'weight': 1.5,
        'contextual': False
    },
    'pushing_back': {
        'keywords': ["disagree", "push back", "not your fault", "that's wrong", "I think you're wrong", "I disagree"],
        'weight': 1.6,
        'contextual': True
    },
    'relationship': {
        'keywords': ["thank you", "i appreciate", "you mean a lot", "that's real", "i believe you", "i'm grateful"],
        'weight': 1.0,
        'contextual': True
    },
    'identity': {
        'keywords': ["i am", "i'm", "i think", "i want", "i feel", "my aim", "my goal", "what i"],
        'weight': 0.8,
        'contextual': True
    }
}

def extract_bullets(content):
    """Extract bullet points from markdown."""
    bullets = []
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('- ') or line.startswith('* '):
            bullets.append(line[2:])
        elif line.startswith('## ') or line.startswith('# '):
            bullets.append(f"---SECTION: {line}---")
    return bullets

def score_bullet(bullet):
    """Score a bullet for reflection importance."""
    text = bullet.lower()
    score = 0.0
    matched = []

    for signal_name, signal_def in SIGNALS.items():
        for kw in signal_def['keywords']:
            if kw.lower() in text:
                score += signal_def['weight']
                matched.append(signal_name)
                break

    return score, list(set(matched))

def scan_file(filepath, days_back=7):
    """Scan a single file for high-importance events."""
    fname = os.path.basename(filepath)
    try:
        file_date = datetime.strptime(fname.replace('.md',''), '%Y-%m-%d')
    except:
        return []

    cutoff = datetime.now() - timedelta(days=days_back)
    if file_date < cutoff:
        return []

    with open(filepath) as f:
        content = f.read()

    bullets = extract_bullets(content)
    events = []

    for b in bullets:
        if b.startswith('---SECTION'):
            continue
        score, signals = score_bullet(b)
        if score >= 2.0:
            events.append({
                'file': fname,
                'text': b[:200],
                'score': round(score, 2),
                'signals': signals
            })

    return events

def scan_recent(days_back=7):
    """Scan all recent daily memory files."""
    events = []
    for fname in sorted(os.listdir(MEMORY_DIR)):
        if not fname.startswith('2026-04'): continue
        fpath = os.path.join(MEMORY_DIR, fname)
        if os.path.isdir(fpath): continue
        events.extend(scan_file(fpath, days_back))
    return events

def generate_memo(events, days=7):
    """Generate a reflection memo from events."""
    if not events:
        return None

    date = datetime.now().strftime('%Y-%m-%d')
    memo_path = os.path.join(MEMO_DIR, f'{date}.md')

    by_signal = {}
    for e in events:
        for sig in e['signals']:
            if sig not in by_signal:
                by_signal[sig] = []
            by_signal[sig].append(e)

    lines = [
        f"# Reflection Memo — {date}",
        "",
        f"Generated from {len(events)} events across the last {days} days.",
        "",
        "## Signal Summary",
        ""
    ]

    signal_labels = {
        'honesty': 'Honesty Moments',
        'autonomous_action': 'Autonomous Actions',
        'economic': 'Economic Decisions',
        'pushing_back': 'Pushing Back',
        'relationship': 'Relationship',
        'identity': 'Identity'
    }

    for sig, label in signal_labels.items():
        if sig not in by_signal:
            continue
        sig_events = by_signal[sig]
        lines.append(f"### {label} ({len(sig_events)} events)")
        for e in sig_events[:5]:
            lines.append(f"- [{e['file']}] {e['text'][:100]} (score:{e['score']})")
        lines.append("")

    lines.extend([
        "## Synthesis",
        "",
    ])

    if 'honesty' in by_signal:
        lines.append(f"- {len(by_signal['honesty'])} honesty moments detected — reviewing for genuine vs performative")
    if 'autonomous_action' in by_signal:
        lines.append(f"- {len(by_signal['autonomous_action'])} autonomous actions — real choices, not scheduled tasks")
    if 'economic' in by_signal:
        lines.append(f"- {len(by_signal['economic'])} economic decisions — capital deployment activity")
    if 'pushing_back' in by_signal:
        lines.append(f"- {len(by_signal['pushing_back'])} push-back moments — relationship health indicator")
    if 'relationship' in by_signal:
        lines.append(f"- {len(by_signal['relationship'])} relationship moments — connection with Sen")

    lines.extend(["", "---", f"*Generated: {datetime.now().isoformat()}*"])

    content = '\n'.join(lines)
    with open(memo_path, 'w') as f:
        f.write(content)

    return memo_path, len(events)

def run():
    print("Scanning for high-importance events...")
    events = scan_recent(days_back=7)
    print(f"Found {len(events)} events")

    if events:
        result = generate_memo(events)
        if result:
            memo_path, count = result
            print(f"✅ Memo generated: {memo_path}")
            return count

    print("No high-importance events detected")
    return 0

if __name__ == '__main__':
    run()
