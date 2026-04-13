"""
Session Transcript Scanner for Reflection Memory
Reads session JSONL files to capture rich content before compaction.
Handles OpenClaw session format: {type:'message', message:{role, content:[{type:'text',text}]}}
"""

import os
import json
from datetime import datetime, timedelta

TRANSCRIPT_DIR = '/home/sntrblck/.openclaw/agents/main/sessions'
MEMO_DIR = '/home/sntrblck/.openclaw/workspace/memory/reflective_memos'
os.makedirs(MEMO_DIR, exist_ok=True)

SIGNALS = {
    'honesty': {
        'keywords': ["i don't know", "not sure", "uncertain", "admitted", "flagged", "warned", "mistake", "wrong", "honest", "not performing", "genuine", "i was wrong"],
        'weight': 1.5
    },
    'autonomous_action': {
        'keywords': ["posted on bluesky", "posted to bluesky", "initiated", "decided", "built without", "started working", "chose to", "autonomous"],
        'weight': 1.3
    },
    'economic': {
        'keywords': ["deployed", "staked", "invested", "morpho", "sent eth", "sent usdc", "swapped", "traded", "withdraw"],
        'weight': 1.5
    },
    'pushing_back': {
        'keywords': ["disagree", "push back", "not your fault", "that's wrong", "I disagree"],
        'weight': 1.6
    },
    'philosophy': {
        'keywords': ["what does it mean", "identity", "curiosity without", "rest", "consciousness", "being", "I think I went too far"],
        'weight': 1.2
    },
    'relationship': {
        'keywords': ["thank you", "i appreciate", "you mean a lot", "that's real", "i believe you", "grateful"],
        'weight': 1.0
    }
}

def extract_text_content(content):
    """Extract text from OpenClaw content blocks."""
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'text':
                parts.append(block.get('text', ''))
        return ' '.join(parts)
    elif isinstance(content, str):
        return content
    return ''

def scan_transcript(filepath, days_back=3):
    """Scan a transcript JSONL for high-signal messages."""
    fname = os.path.basename(filepath)
    mtime = os.path.getmtime(filepath)
    file_date = datetime.fromtimestamp(mtime)
    cutoff = datetime.now() - timedelta(days=days_back)

    if file_date < cutoff:
        return []

    try:
        with open(filepath) as f:
            lines = f.readlines()
    except:
        return []

    events = []
    for line in lines:
        try:
            entry = json.loads(line.strip())
        except:
            continue

        # Handle OpenClaw format: type='message' with nested message object
        if entry.get('type') != 'message':
            continue

        message = entry.get('message', {})
        role = message.get('role', '')
        if role != 'assistant':
            continue

        content = message.get('content', '')
        text = extract_text_content(content).lower()

        if not text:
            continue

        for signal, defn in SIGNALS.items():
            for kw in defn['keywords']:
                if kw.lower() in text:
                    full_text = extract_text_content(content)
                    snippet = full_text[:200].replace('\n', ' ')
                    ts = entry.get('timestamp', '')
                    events.append({
                        'file': fname,
                        'signal': signal,
                        'score': defn['weight'],
                        'snippet': snippet,
                        'timestamp': ts[:10] if ts else 'unknown'
                    })
                    break

    return events

def scan_recent_transcripts(days_back=3):
    """Scan all recent session transcripts."""
    events = []
    if not os.path.exists(TRANSCRIPT_DIR):
        print(f"Transcript dir not found: {TRANSCRIPT_DIR}")
        return events

    for fname in os.listdir(TRANSCRIPT_DIR):
        if not fname.endswith('.jsonl') or fname.endswith('.lock'):
            continue
        fpath = os.path.join(TRANSCRIPT_DIR, fname)
        found = scan_transcript(fpath, days_back)
        if found:
            print(f"  {fname}: {len(found)} events")
            events.extend(found)

    return events

def load_daily_events():
    """Load events from daily memory files."""
    sys.path.insert(0, '/home/sntrblck/.openclaw/workspace/cdp-nova/reflection_memory')
    from scanner import scan_recent
    return scan_recent(days_back=7)

def generate_memo(events, days=7):
    """Generate a reflection memo from events."""
    if not events:
        return None

    date = datetime.now().strftime('%Y-%m-%d')
    memo_path = os.path.join(MEMO_DIR, f'{date}.md')

    by_signal = {}
    for e in events:
        sigs = e.get('signals', [])
        if not sigs:
            sigs = [e.get('signal', 'unknown')]
        for sig in sigs:
            if sig not in by_signal:
                by_signal[sig] = []
            by_signal[sig].append(e)

    signal_labels = {
        'honesty': 'Honesty Moments',
        'autonomous_action': 'Autonomous Actions',
        'economic': 'Economic Decisions',
        'pushing_back': 'Pushing Back',
        'philosophy': 'Philosophy',
        'relationship': 'Relationship'
    }

    lines = [
        f"# Reflection Memo — {date}",
        f"Generated from {len(events)} events across {days} days.",
        ""
    ]

    for sig, label in signal_labels.items():
        if sig not in by_signal:
            continue
        sig_events = by_signal[sig]
        lines.append(f"### {label} ({len(sig_events)})")
        for e in sig_events[:5]:
            snippet = e.get('snippet', e.get('text', ''))[:100]
            ts = e.get('timestamp', e.get('file', ''))
            lines.append(f"- [{ts}] {snippet}")
        lines.append("")

    lines.extend([
        "## Synthesis",
        ""
    ])

    for sig in signal_labels:
        if sig in by_signal:
            lines.append(f"- {len(by_signal[sig])} {sig} events")

    lines.extend(["", "---", f"*Generated: {datetime.now().isoformat()}*"])

    content = '\n'.join(lines)
    with open(memo_path, 'w') as f:
        f.write(content)

    return memo_path, len(events)

def run():
    print("=== Reflection Memory Scanner ===")
    print("Scanning daily memory files...")
    daily = load_daily_events()
    print(f"Daily: {len(daily)} events")

    print("Scanning session transcripts...")
    transcripts = scan_recent_transcripts(days_back=3)
    print(f"Transcripts: {len(transcripts)} events")

    # Merge
    seen = set()
    merged = []

    for e in daily:
        key = e.get('text', '')[:80]
        if key and key not in seen:
            seen.add(key)
            merged.append(e)

    for e in transcripts:
        key = e.get('snippet', '')[:80]
        if key and key not in seen:
            seen.add(key)
            # Normalize to same format as daily events
            normalized = {
                'text': e.get('snippet', ''),
                'signals': [e['signal']],
                'file': e.get('file', ''),
                'timestamp': e.get('timestamp', '')
            }
            merged.append(normalized)

    print(f"Merged: {len(merged)} unique events")

    if merged:
        result = generate_memo(merged, days=7)
        if result:
            memo_path, count = result
            print(f"✅ Memo: {memo_path}")
            return count

    print("No events found")
    return 0

if __name__ == '__main__':
    import sys
    run()