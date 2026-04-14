#!/usr/bin/env python3
"""
Nova's Daily Pulse Generator

Scans the day's artifacts and produces a concise 3-5 sentence summary:
- What Nova accomplished
- What didn't work
- What's worth attention

Data sources:
- memory/YYYY-MM-DD.md (daily log)
- memory/reflective_memos/YYYY-MM-DD.md (reflection signals)
- cdp-nova/logs/bluesky_monitor.jsonl (social activity)
- cdp-nova/treasury.db (financial state)
- memory/execution_logs.db (cron/system activity)
"""

import sys
import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get('OPENCLAW_WORKSPACE', '/home/sntrblck/.openclaw/workspace'))
MEMORY_DIR = WORKSPACE / 'memory'
CDP_DIR = WORKSPACE / 'cdp-nova'
REFLECTION_DIR = MEMORY_DIR / 'reflective_memos'

def get_date_arg():
    """Get date from arg or default to today."""
    if len(sys.argv) > 1:
        return sys.argv[1], False
    return datetime.now().strftime('%Y-%m-%d'), False

def get_week_dates(date_str):
    """Get the 7 dates ending with date_str."""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return [(dt - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]

def read_daily_log(date_str):
    """Read the day's memory log."""
    path = MEMORY_DIR / f'{date_str}.md'
    if not path.exists():
        return None
    with open(path) as f:
        return f.read()

def read_reflection_memo(date_str):
    """Read the day's reflection memo."""
    path = REFLECTION_DIR / f'{date_str}.md'
    if not path.exists():
        return None
    with open(path) as f:
        return f.read()

def get_bluesky_activity(date_str):
    """Count Bluesky posts found and high-intent from today."""
    log_path = CDP_DIR / 'logs' / 'bluesky_monitor.jsonl'
    if not log_path.exists():
        return {'posts_found': 0, 'high_intent': 0}
    
    posts_found = 0
    high_intent = 0
    target_date = date_str
    
    with open(log_path) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                found_at = entry.get('found_at', '')[:10]
                if found_at == target_date:
                    posts_found += 1
                    if entry.get('highIntent'):
                        high_intent += 1
            except (json.JSONDecodeError, KeyError):
                continue
    
    return {'posts_found': posts_found, 'high_intent': high_intent}

def get_treasury_state():
    """Get current portfolio value and key holdings."""
    db_path = CDP_DIR / 'treasury.db'
    if not db_path.exists():
        return None
    
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    
    try:
        # Get holdings with prices
        cur.execute('''
            SELECT h.wallet, h.asset, h.amount, p.price 
            FROM holdings h 
            JOIN prices p ON h.asset = p.asset
            ORDER BY h.wallet, h.asset
        ''')
        holdings = cur.fetchall()
        
        total_value = 0
        wallet_values = {}
        for wallet, asset, amount, price in holdings:
            value = float(amount) * float(price) if price else 0
            total_value += value
            if wallet not in wallet_values:
                wallet_values[wallet] = 0
            wallet_values[wallet] += value
        
        return {
            'total_value': total_value,
            'wallets': wallet_values,
            'holdings_count': len(holdings)
        }
    except Exception as e:
        return {'error': str(e)}
    finally:
        conn.close()

def get_cron_activity(date_str):
    """Get cron runs for the day."""
    db_path = MEMORY_DIR / 'execution_logs.db'
    if not db_path.exists():
        return {'runs': 0, 'types': set()}
    
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    
    try:
        # Parse logs for the target date
        cur.execute('''
            SELECT event_type, details FROM execution_logs 
            WHERE timestamp LIKE ?
            ORDER BY timestamp DESC
        ''', (f'{date_str}%',))
        rows = cur.fetchall()
        
        types = set()
        for event_type, details in rows:
            types.add(event_type)
        
        return {'runs': len(rows), 'types': types}
    except Exception as e:
        return {'runs': 0, 'types': set(), 'error': str(e)}
    finally:
        conn.close()

import re

def extract_sections(text):
    """Extract sections from markdown text."""
    if not text:
        return {}
    sections = {}
    current_header = 'header'
    current_lines = []
    for line in text.split('\n'):
        if line.startswith('## '):
            if current_lines:
                sections[current_header] = '\n'.join(current_lines).strip()
            # Strip timestamp prefix like "10:03 - " or "14:30 - "
            header = line[3:].strip()
            header = re.sub(r'^\d{1,2}:\d{2}\s*-\s*', '', header)
            current_header = header
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections[current_header] = '\n'.join(current_lines).strip()
    return sections

def extract_builds(text):
    """Find what was built/accomplished from daily log sections."""
    if not text:
        return [], []
    
    accomplished = []
    failed = []
    
    sections = extract_sections(text)
    
    for header, body in sections.items():
        header_lower = header.lower()
        body_lower = body.lower()
        combined = header_lower + ' ' + body_lower
        
        # Built/shipped/created — match on section header or first line of body
        # Skip headers that are file lists or metadata
        skip_header_words = ['files created', 'files modified', 'open items', 'crons active', 'decisions made']
        if any(w in header_lower for w in skip_header_words):
            pass  # skip these headers
        elif any(w in header_lower for w in ['built', 'shipped', 'created', 'deployed', 'wired', 'fixed', 'completed', 'installed', 'registered']):
            accomplished.append(header.strip())
        elif any(w in combined for w in ['built', 'shipped', 'deployed', 'created']):
            for line in body.split('\n'):
                line = line.strip()
                line_lower = line.lower()
                if not line or line_lower.startswith('#') or line_lower.startswith('-') or line_lower.startswith('*'):
                    continue
                if len(line) < 20:  # skip short fragments
                    continue
                if line_lower.startswith(('read', 'see ', 'note:', 'todo:', 'check', 'files created', 'files modified')):
                    continue
                # Skip tool descriptions: "Built to bundle/read/" is docs, not accomplishments
                if re.match(r'^built to \w+', line_lower):
                    continue
                if any(w in line_lower for w in ['built', 'shipped', 'deployed', 'created']):
                    if len(line) > 120:
                        line = line[:117] + '...'
                    accomplished.append(line)
                    break
        
        # Failed/didn't work/abandoned
        if any(w in combined for w in ['fail', 'didn\'t work', 'error', 'abandon', 'broke', 'conflict', 'reject']):
            # Get first line that mentions the failure
            for line in body.split('\n'):
                line = line.strip()
                line_lower = line.lower()
                if not line or line_lower.startswith('#') or line_lower.startswith('-') or line_lower.startswith('*'):
                    continue
                if any(w in line_lower for w in ['fail', 'didn\'t work', 'error', 'broke', 'conflict']):
                    if len(line) > 100:
                        line = line[:97] + '...'
                    failed.append(line)
                    break
    
    return accomplished, failed

def generate_pulse(date_str):
    """Generate the daily pulse summary."""
    # Gather data
    daily_log = read_daily_log(date_str)
    reflection = read_reflection_memo(date_str)
    bsky = get_bluesky_activity(date_str)
    treasury = get_treasury_state()
    cron = get_cron_activity(date_str)
    
    if not daily_log:
        return f"**Nova Daily Pulse — {date_str}**\n\nNo activity logged. Quiet day."
    
    # Extract key events
    accomplished, failed = extract_builds(daily_log)
    
    # Count log entries (## headers = distinct events)
    sections = extract_sections(daily_log)
    event_count = len([k for k in sections.keys() if k != 'header'])
    
    # Build the pulse
    parts = []
    
    # 1. Activity overview
    activity_parts = [f"{event_count} event{'s' if event_count != 1 else ''} logged"]
    if cron.get('runs', 0) > 0:
        activity_parts.append(f"{cron['runs']} cron run{'s' if cron['runs'] != 1 else ''}")
    if bsky['posts_found'] > 0:
        activity_parts.append(f"{bsky['posts_found']} Bluesky post{'s' if bsky['posts_found'] != 1 else ''} monitored ({bsky['high_intent']} high-intent)")
    
    parts.append(f"{' · '.join(activity_parts)}.")
    
    # 2. What was built/accomplished
    if accomplished:
        # Deduplicate and take top 3
        unique = list(dict.fromkeys(accomplished))[:3]
        parts.append(f"Shipped: {'; '.join(unique)}.")
    elif event_count > 0:
        # Summarize section headers — prefer activity-like ones
        all_headers = [k for k in sections.keys() if k != 'header']
        # Filter out metadata-like headers
        skip_patterns = ['open items', 'crons active', 'decisions made', 'pending', 'todo']
        activity_headers = [h for h in all_headers if not any(p in h.lower() for p in skip_patterns)]
        # Take up to 3
        display = (activity_headers if activity_headers else all_headers)[:3]
        # Clean up cron headers
        cleaned = []
        for h in display:
            # Remove cron timestamps like "(04:00 UTC / 12:00 AM EDT)"
            clean = re.sub(r'\s*\([^)]*(?:UTC|EDT|EST|ET)[^)]*\)', '', h).strip()
            # Remove success/fail suffixes
            clean = re.sub(r'\s*-\s*(SUCCESS|FAILED|ERROR)\s*$', '', clean)
            # Remove Cron: prefix
            clean = re.sub(r'^Cron:\s*', '', clean).strip()
            if clean and clean not in cleaned:
                cleaned.append(clean)
        if cleaned:
            parts.append(f"Focus: {', '.join(cleaned)}.")
    elif event_count > 0:
        # Summarize section headers
        headers = [k for k in sections.keys() if k != 'header'][:3]
        parts.append(f"Focus areas: {', '.join(headers)}.")
    
    # 3. What didn't work
    if failed:
        sig = failed[:2]
        parts.append(f"Didn't land: {'; '.join(sig)}.")
    
    # 4. Reflection signals
    if reflection:
        ref_sections = extract_sections(reflection)
        signal_counts = []
        for k, v in ref_sections.items():
            if k in ('Synthesis', 'header'):
                continue
            # Extract the count from the header like "Autonomous Action (2)"
            match = re.search(r'\((\d+)\)', k)
            if match:
                count = int(match.group(1))
                cat_name = re.sub(r'\s*\(\d+\)', '', k).lower()
                if count > 0:
                    signal_counts.append(f"{cat_name} ({count})")
            else:
                # Count lines starting with -
                count = len([l for l in v.split('\n') if l.strip().startswith('-')])
                if count > 0:
                    signal_counts.append(f"{k.lower()} ({count})")
        if signal_counts:
            parts.append(f"Signals: {', '.join(signal_counts)}.")
    
    # 5. Portfolio
    if treasury and 'total_value' in treasury:
        total = treasury['total_value']
        if total > 0:
            parts.append(f"Portfolio: ${total:.2f}.")
    
    pulse = f"**Nova Daily Pulse — {date_str}**\n\n{' '.join(parts)}"
    
    # Flag anything worth attention
    attention_items = []
    if bsky.get('high_intent', 0) > 0:
        attention_items.append(f"{bsky['high_intent']} high-intent Bluesky post(s) found")
    if failed:
        attention_items.append("failures need follow-up")
    
    if attention_items:
        pulse += f"\n\n⚡ Attention: {'; '.join(attention_items)}."
    
    return pulse

def main():
    date_str, _ = get_date_arg()
    
    # Check for --week flag
    if '--week' in sys.argv:
        dates = get_week_dates(date_str)
        all_shipped = []
        all_failed = []
        total_events = 0
        total_bsky = {'posts_found': 0, 'high_intent': 0}
        all_signals = []
        days_active = 0
        
        for d in dates:
            log = read_daily_log(d)
            if log:
                days_active += 1
            accomplished, failed = extract_builds(log or '')
            all_shipped.extend(accomplished)
            all_failed.extend(failed)
            sections = extract_sections(log or '')
            total_events += len([k for k in sections.keys() if k != 'header'])
            bsky = get_bluesky_activity(d)
            total_bsky['posts_found'] += bsky['posts_found']
            total_bsky['high_intent'] += bsky['high_intent']
            
            reflection = read_reflection_memo(d)
            if reflection:
                ref_sections = extract_sections(reflection)
                for k, v in ref_sections.items():
                    if k in ('Synthesis', 'header'):
                        continue
                    match = re.search(r'\((\d+)\)', k)
                    if match:
                        cat_name = re.sub(r'\s*\(\d+\)', '', k).lower()
                        all_signals.append(cat_name)
        
        # Build weekly pulse
        parts = []
        parts.append(f"{days_active}/7 days active · {total_events} total events · {total_bsky['posts_found']} Bluesky posts monitored ({total_bsky['high_intent']} high-intent).")
        
        # Deduplicate shipped items
        unique_shipped = list(dict.fromkeys(all_shipped))[:5]
        if unique_shipped:
            parts.append(f"Shipped: {'; '.join(unique_shipped)}.")
        
        unique_failed = list(dict.fromkeys(all_failed))[:3]
        if unique_failed:
            parts.append(f"Didn't land: {'; '.join(unique_failed)}.")
        
        if all_signals:
            from collections import Counter
            sig_counts = Counter(all_signals)
            sig_str = ', '.join(f"{k} ({v})" for k, v in sig_counts.most_common())
            parts.append(f"Signals: {sig_str}.")
        
        treasury = get_treasury_state()
        if treasury and 'total_value' in treasury:
            total = treasury['total_value']
            if total > 0:
                parts.append(f"Portfolio: ${total:.2f}.")
        
        start = dates[0]
        end = dates[-1]
        pulse = f"**Nova Weekly Pulse — {start} to {end}**\n\n{' '.join(parts)}"
        
        # Save
        pulse_dir = MEMORY_DIR / 'pulses'
        pulse_dir.mkdir(exist_ok=True)
        pulse_path = pulse_dir / f'week-{end}.md'
        with open(pulse_path, 'w') as f:
            f.write(pulse + '\n')
        
        print(pulse)
        print(f"\n[Saved to {pulse_path}]")
    else:
        # Daily pulse
        pulse = generate_pulse(date_str)
        
        # Save to file
        pulse_dir = MEMORY_DIR / 'pulses'
        pulse_dir.mkdir(exist_ok=True)
        pulse_path = pulse_dir / f'{date_str}.md'
        with open(pulse_path, 'w') as f:
            f.write(pulse + '\n')
        
        print(pulse)
        print(f"\n[Saved to {pulse_path}]")

if __name__ == '__main__':
    main()