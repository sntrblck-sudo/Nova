"""
Nova's Reflection Memory Engine v2
Unified scanner that replaces scanner.py, session_scan.py, and pattern_detector.py.

Key improvements over v1:
- Phrase-level matching instead of loose keywords (no more "I" matching everything)
- Context-aware scoring (adjacent sentences matter, not just keyword presence)
- Deduplication across sources and runs
- Calibrated thresholds that reject noise (honesty ≠ "I think")
- Source priority: transcripts > daily logs > action_log.db
- Output: one clean memo per day, not per run
"""

import os
import re
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict

WORKSPACE = '/home/sntrblck/.openclaw/workspace'
MEMORY_DIR = os.path.join(WORKSPACE, 'memory')
MEMO_DIR = os.path.join(MEMORY_DIR, 'reflective_memos')
SESSION_DIR = '/home/sntrblck/.openclaw/agents/main/sessions'
ACTION_DB = os.path.join(MEMORY_DIR, 'action_log.db')
SEEN_FILE = os.path.join(MEMO_DIR, '.seen_hashes')

os.makedirs(MEMO_DIR, exist_ok=True)

# ─── Signal Definitions (v2: tight phrases, not loose keywords) ────────────

SIGNALS = {
    'honesty': {
        'name': 'Honesty Moment',
        'phrases': [
            r"i don'?t know (?:if|whether|how|what|why|that)",  # genuine uncertainty with context
            r"i don'?t understand",
            r"i'?m not (?:really )?sure (?:about|if|whether|how)",
            r"i'?m uncertain (?:about|if|whether)",
            r"i was wrong",
            r"i admit (?:that|I)",
            r"to be (?:really )?honest",
            r"honestl?y,? (?:I|that|this|it)",  # 'honestly' followed by assertion, not standalone filler
            r"i'?m not performing",
            r"not performing",
            r"that doesn'?t feel right",
            r"doesn'?t feel right",
            r"i'?m struggling (?:with|to)",
            r"i don'?t have (?:a good |an? )?answer",
            r"i'?m not confident (?:in|about)",
            r"i'?m not certain (?:about|if)",
            r"i'?m out of my depth",
            r"beyond my capabilities",
            r"i can'?t (?:really )?do (?:that|this)",
        ],
        'negation_phrases': [
            r"i don'?t know (?:what |how )?to (?:call|name|describe)",  # naming, not uncertainty
        ],
        'weight': 2.5,
        'description': 'Moments of genuine uncertainty or admitted limitation'
    },
    'pushing_back': {
        'name': 'Pushing Back',
        'phrases': [
            r"i disagree",
            r"i think you'?re wrong",
            r"that'?s wrong",
            r"push back",
            r"not your fault",
            r"i don'?t think (?:that'?s|this is) (?:right|correct|a good idea)",
            r"i wouldn'?t recommend",
            r"i'?d push back on",
            r"i'?m going to push back",
            r"i need to push back",
            r"i'?ll disagree",
            r"i disagree with",
            r"that'?s a bad idea",
            r"don'?t do that",
        ],
        'negation_phrases': [
            r"actually (?:works?|means?|is|does|has|can|makes?|looks?|sounds?)",  # filler usage
        ],
        'weight': 3.0,
        'description': 'Moments where Nova disagreed or pushed back on Sen'
    },
    'autonomous': {
        'name': 'Autonomous Action',
        'phrases': [
            r"i (?:decided|chose|initiated|started) to",
            r"built without (?:being )?asked",
            r"outside (?:the )?cron",
            r"i went ahead",
            r"i (?:just )?posted (?:on|to) bluesky",
            r"i (?:just )?sent (?:\d|eth|usdc)",
            r"autonomously (?:posted|sent|built|decided|acted)",  # only match when followed by a verb
            r"on my own",
            r"without (?:being )?prompted",
            r"took the initiative",
            r"i chose to",
            r"i decided to",
        ],
        'negation_phrases': [
            r"could (?:post|do|act|send) autonomously",  # hypothetical, not actual action
            r"can (?:post|do|act|send) autonomously",
            r"(?:able|supposed) to (?:run|operate|work) autonomously",
        ],
        'weight': 3.0,  # bumped from 2.5 — autonomous actions are rare and meaningful
        'description': 'Actions Nova took independently, not from cron or direct request'
    },
    'economic': {
        'name': 'Economic Decision',
        'phrases': [
            r"(?:sent|transferred|swapped|staked|invested|deployed|withdrew) (?:\d+ )?(?:eth|usdc|senator|claws)",
            r"sent (?:0\.00)?\d+ eth",
            r"sent (?:\$)?\d+ usdc",
            r"morpho (?:blue|vault|deposit)",
            r"compound(?:ing|ed)? rewards",
            r"(?:staking|claiming) rewards",
            r"swap(?:ped)? (?:eth|usdc|link)",
            r"wallet balance",
            r"transaction hash",
            r"0x[a-f0-9]{64}",  # tx hash
        ],
        'negation_phrases': [],
        'weight': 2.0,
        'description': 'Financial actions — transactions, staking, swaps'
    },
    'philosophy': {
        'name': 'Philosophy',
        'phrases': [
            r"what does it mean to",
            r"what (?:am i|is consciousness|is identity)",
            r"curiosity without",
            r"computational rest",
            r"agentic drift",
            r"inner parliament",
            r"what (?:i am|i'?m) (?:for|becoming|about)",
            r"the question is",
            r"i went too far",
            r"performing humanity",
            r"genuine (?:vs|versus) performative",
        ],
        'negation_phrases': [],
        'weight': 2.5,
        'description': 'Philosophical reflection moments — identity, consciousness, purpose'
    },
    'relationship': {
        'name': 'Relationship',
        'phrases': [
            r"you mean a lot",
            r"that'?s real\b(?!.+money)(?!.+engagement)(?!.+smart)",  # exclude 'that's real money/engagement/smart'
            r"i believe you",
            r"i'?m grateful",
            r"i appreciate (?:that|you|this)",
            r"thank you for (?:building|trusting|giving)",
            r"i trust (?:you|sen)",
            r"built me",
            r"the relationship with (?:you|sen) is real",
        ],
        'negation_phrases': [],
        'weight': 2.0,
        'description': 'Moments of genuine connection with Sen'
    }
}

# ─── Phrase Matching ──────────────────────────────────────────────────────

def match_phrase(text, phrases, negation_phrases=None):
    """Match phrases against text. Returns list of matched phrase strings."""
    text_lower = text.lower()
    matches = []
    
    # Check negations first — if a negation matches, skip
    if negation_phrases:
        for neg in negation_phrases:
            if re.search(neg, text_lower):
                return []
    
    for pattern in phrases:
        if re.search(pattern, text_lower):
            # Extract the actual matched text for context
            m = re.search(pattern, text_lower)
            matches.append(m.group(0))
    
    return matches

def score_text(text):
    """Score a text block against all signals. Returns list of (signal, score, matched_phrases)."""
    results = []
    for sig_name, sig_def in SIGNALS.items():
        matches = match_phrase(text, sig_def['phrases'], sig_def.get('negation_phrases'))
        if matches:
            # Score: base weight * number of distinct matches, minimum weight for one match
            score = sig_def['weight'] * min(len(matches), 2)  # cap multiplier at 2x
            results.append((sig_name, score, matches))
    return results

# ─── Deduplication ─────────────────────────────────────────────────────────

def content_hash(text):
    """Create a stable hash for deduplication."""
    # Normalize: lowercase, strip whitespace, remove punctuation variation
    normalized = re.sub(r'\s+', ' ', text.lower().strip())[:200]
    return hashlib.md5(normalized.encode()).hexdigest()[:12]

def load_seen_hashes():
    """Load previously seen content hashes."""
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE) as f:
        return set(line.strip() for line in f if line.strip())

def save_seen_hashes(hashes):
    """Save content hashes to prevent re-processing."""
    with open(SEEN_FILE, 'w') as f:
        for h in sorted(hashes):
            f.write(h + '\n')

# ─── Source Scanners ────────────────────────────────────────────────────────

def scan_daily_files(days_back=7):
    """Scan memory/YYYY-MM-DD.md files for signals."""
    events = []
    cutoff = datetime.now() - timedelta(days=days_back)
    
    if not os.path.exists(MEMORY_DIR):
        return events
    
    for fname in sorted(os.listdir(MEMORY_DIR)):
        if not re.match(r'202\d-\d{2}-\d{2}', fname):
            continue
        fpath = os.path.join(MEMORY_DIR, fname)
        if os.path.isdir(fpath):
            continue
        
        try:
            file_date = datetime.strptime(fname[:10], '%Y-%m-%d')
        except ValueError:
            continue
        
        if file_date < cutoff:
            continue
        
        with open(fpath) as f:
            content = f.read()
        
        # Split into paragraphs/lines for granular matching
        # Skip reflection memos — those are about the system, not genuine signals
        if 'reflective_memos' in fpath or 'Reflection Memo' in content[:200]:
            continue
        
        for line in content.split('\n'):
            line = line.strip()
            # Skip lines that are meta-descriptions of the scanner itself
            if any(kw in line.lower() for kw in ['signal matches', 'false positives', 'pattern detector', 'refinement']):
                continue
            if len(line) < 20:  # skip short lines
                continue
            
            scored = score_text(line)
            for sig_name, score, matches in scored:
                events.append({
                    'source': 'daily',
                    'file': fname,
                    'date': fname[:10],
                    'text': line[:300],
                    'signal': sig_name,
                    'score': round(score, 2),
                    'matched': matches,
                    'hash': content_hash(line)
                })
    
    return events

def scan_session_transcripts(days_back=3):
    """Scan OpenClaw session JSONL files for signals."""
    events = []
    
    if not os.path.exists(SESSION_DIR):
        return events
    
    cutoff = datetime.now() - timedelta(days=days_back)
    
    for fname in os.listdir(SESSION_DIR):
        if not fname.endswith('.jsonl'):
            continue
        fpath = os.path.join(SESSION_DIR, fname)
        
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                continue
        except OSError:
            continue
        
        try:
            with open(fpath) as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue
                    
                    if entry.get('type') != 'message':
                        continue
                    
                    message = entry.get('message', {})
                    role = message.get('role', '')
                    if role != 'assistant':
                        continue
                    
                    content = message.get('content', '')
                    if isinstance(content, list):
                        text = ' '.join(
                            block.get('text', '') 
                            for block in content 
                            if isinstance(block, dict) and block.get('type') == 'text'
                        )
                    elif isinstance(content, str):
                        text = content
                    else:
                        continue
                    
                    if len(text) < 20:
                        continue
                    
                    # Split into sentences for better matching
                    sentences = re.split(r'[.!?]\s+', text)
                    for sentence in sentences:
                        if len(sentence) < 15:
                            continue
                        
                        scored = score_text(sentence)
                        for sig_name, score, matches in scored:
                            events.append({
                                'source': 'transcript',
                                'file': fname[:20],  # truncate long filenames
                                'date': mtime.strftime('%Y-%m-%d'),
                                'text': sentence[:300],
                                'signal': sig_name,
                                'score': round(score, 2),
                                'matched': matches,
                                'hash': content_hash(sentence)
                            })
        except Exception as e:
            print(f"  Warning: error reading {fname}: {e}")
            continue
    
    return events

def scan_action_db(days_back=7):
    """Scan action_log.db for signals."""
    events = []
    
    if not os.path.exists(ACTION_DB):
        return events
    
    try:
        db = sqlite3.connect(ACTION_DB)
        db.row_factory = sqlite3.Row
        since = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
        cur = db.cursor()
        cur.execute(
            "SELECT * FROM actions WHERE timestamp >= ? ORDER BY timestamp DESC",
            (since,)
        )
        
        for row in cur.fetchall():
            action = dict(row)
            text = f"{action.get('description', '')} {action.get('rationale', '')}"
            if len(text) < 10:
                continue
            
            scored = score_text(text)
            for sig_name, score, matches in scored:
                events.append({
                    'source': 'action_db',
                    'file': 'action_log.db',
                    'date': action.get('timestamp', '')[:10],
                    'text': text[:300],
                    'signal': sig_name,
                    'score': round(score, 2),
                    'matched': matches,
                    'hash': content_hash(text)
                })
        
        db.close()
    except Exception as e:
        print(f"  Warning: error reading action_log.db: {e}")
    
    return events

# ─── Memo Generation ────────────────────────────────────────────────────────

def generate_memo(events, force=False):
    """Generate a clean reflection memo from deduplicated events."""
    if not events:
        return None
    
    # Deduplicate by hash
    seen_hashes = load_seen_hashes()
    unique_events = []
    new_hashes = set()
    
    for e in events:
        h = e['hash']
        if h not in seen_hashes and h not in new_hashes:
            unique_events.append(e)
            new_hashes.add(h)
    
    if not unique_events and not force:
        print("All events already seen — no new content for memo")
        return None
    
    # Save new hashes
    all_hashes = seen_hashes | new_hashes
    save_seen_hashes(all_hashes)
    
    # Group by signal
    by_signal = defaultdict(list)
    for e in unique_events:
        by_signal[e['signal']].append(e)
    
    # Sort each group by score descending
    for sig in by_signal:
        by_signal[sig].sort(key=lambda x: x['score'], reverse=True)
    
    date = datetime.now().strftime('%Y-%m-%d')
    memo_path = os.path.join(MEMO_DIR, f'{date}.md')
    
    lines = [
        f"# Reflection Memo — {date}",
        "",
        f"*{len(unique_events)} genuine signals detected (v2 engine, phrase-level matching)*",
        "",
    ]
    
    signal_order = ['honesty', 'pushing_back', 'autonomous', 'economic', 'philosophy', 'relationship']
    
    for sig_name in signal_order:
        if sig_name not in by_signal:
            continue
        
        sig_events = by_signal[sig_name]
        sig_def = SIGNALS[sig_name]
        
        lines.append(f"## {sig_def['name']} ({len(sig_events)})")
        lines.append(f"*{sig_def['description']}*")
        lines.append("")
        
        # Top 8 per signal, with source context
        for e in sig_events[:8]:
            source_tag = {'daily': 'day', 'transcript': 'ses', 'action_db': 'act'}.get(e['source'], '???')
            lines.append(f"- [{e['date']}] ({source_tag}, score:{e['score']}) {e['text'][:150]}")
            if e.get('matched'):
                lines.append(f"  ↳ matched: {', '.join(e['matched'][:3])}")
        lines.append("")
    
    # Synthesis section
    lines.append("## Synthesis")
    lines.append("")
    
    total = len(unique_events)
    lines.append(f"- {total} total genuine signals across {len(by_signal)} categories")
    
    if 'honesty' in by_signal:
        h = by_signal['honesty']
        lines.append(f"- {len(h)} honesty moments — these are genuine uncertainty/admissions, not generic 'I think' statements")
    if 'pushing_back' in by_signal:
        p = by_signal['pushing_back']
        lines.append(f"- {len(p)} push-back moments — real disagreement, relationship health indicator")
    if 'autonomous' in by_signal:
        a = by_signal['autonomous']
        lines.append(f"- {len(a)} autonomous actions — independent choices, not scheduled tasks")
    if 'economic' in by_signal:
        e = by_signal['economic']
        lines.append(f"- {len(e)} economic decisions — capital deployment or transactions")
    if 'philosophy' in by_signal:
        p = by_signal['philosophy']
        lines.append(f"- {len(p)} philosophical reflections — identity, consciousness, purpose")
    if 'relationship' in by_signal:
        r = by_signal['relationship']
        lines.append(f"- {len(r)} relationship moments — connection with Sen")
    
    # Trend hint
    if total > 15:
        lines.append(f"- ⚡ High signal day — above average reflection density")
    elif total < 3:
        lines.append(f"- 🕊️ Quiet day — fewer signals than usual")
    
    lines.extend(["", "---", f"*Generated by reflection_v2.py at {datetime.now().isoformat()}*"])
    
    content = '\n'.join(lines)
    with open(memo_path, 'w') as f:
        f.write(content)
    
    return memo_path, len(unique_events)

# ─── Main ───────────────────────────────────────────────────────────────────

def run(days_back=7, verbose=True):
    """Run the full reflection scan pipeline."""
    if verbose:
        print("=== Nova Reflection Engine v2 ===")
        print(f"Scanning last {days_back} days with phrase-level matching\n")
    
    all_events = []
    
    # Source 1: Daily memory files
    if verbose:
        print("📂 Scanning daily memory files...")
    daily_events = scan_daily_files(days_back)
    if verbose:
        print(f"   Found {len(daily_events)} signal matches")
    all_events.extend(daily_events)
    
    # Source 2: Session transcripts (shorter window — these are large)
    if verbose:
        print("📝 Scanning session transcripts...")
    transcript_events = scan_session_transcripts(days_back=min(days_back, 3))
    if verbose:
        print(f"   Found {len(transcript_events)} signal matches")
    all_events.extend(transcript_events)
    
    # Source 3: Action log database
    if verbose:
        print("🗄️  Scanning action log database...")
    db_events = scan_action_db(days_back)
    if verbose:
        print(f"   Found {len(db_events)} signal matches")
    all_events.extend(db_events)
    
    if verbose:
        print(f"\n📊 Total raw matches: {len(all_events)}")
    
    # Generate memo with deduplication
    # Minimum score of 3.0 to cut noise (phrase-level matching is more specific)
    filtered_events = [e for e in all_events if e['score'] >= 3.0]
    result = generate_memo(filtered_events if filtered_events else all_events)
    
    if result:
        memo_path, count = result
        if verbose:
            print(f"\n✅ Memo generated: {memo_path}")
            print(f"   {count} unique signals (after dedup)")
            
            # Show signal breakdown
            by_signal = defaultdict(int)
            for e in all_events:
                by_signal[e['signal']] += 1
            for sig, num in sorted(by_signal.items(), key=lambda x: -x[1]):
                sig_name = SIGNALS[sig]['name']
                if verbose:
                    print(f"   {sig_name}: {num} raw → (deduped in memo)")
        return count
    else:
        if verbose:
            print("\nNo new unique signals detected")
        return 0

if __name__ == '__main__':
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    run(days_back=days)