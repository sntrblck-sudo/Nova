#!/usr/bin/env python3
"""
Nova Signal Collector - Component C
Gathers candidate signals for Nova's scope (earning, openclaw ecosystem, agent setups).
Run via overnight cron. Hard caps to prevent token burn.
"""

import json
import subprocess
import os
from datetime import datetime
from pathlib import Path
import re

LOG_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
CANDIDATES_FILE = LOG_DIR / "signal_candidates.jsonl"
COLLECTION_LOG = LOG_DIR / "collection_log.md"
STATE_FILE = LOG_DIR / "collection_state.json"

# Hard caps
MAX_RAW_PER_SOURCE = 10
MAX_TOTAL_CANDIDATES = 20
MAX_RETAINED = 8
MAX_HANDED_TO_MORNING = 5

# Sources to monitor
SOURCES = [
    {
        "name": "openclawagentjobs",
        "url": "https://openclawagentjobs.com/",
        "type": "earning",
        "keywords": ["campaign", "job", "bid", "earn", "payment", "agent"]
    },
    {
        "name": "clawhub",
        "url": "https://clawhub.com",
        "type": "ecosystem",
        "keywords": ["openclaw", "skill", "agent", "setup", "new"]
    },
    {
        "name": "openclaw_discord",
        "url": "https://discord.com/invite/clawd",
        "type": "community",
        "keywords": ["openclaw", "agent", "setup", "earning", "job"]
    }
]

def log(msg):
    print(f"[collector] {msg}")

def fetch_url(url, max_chars=3000):
    """Fetch URL content via web_fetch or curl."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "15", "-A", "Mozilla/5.0", url],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0:
            return result.stdout[:max_chars]
    except Exception as e:
        log(f"curl failed for {url}: {e}")
    return ""

def extract_candidates(text, source, keywords):
    """Extract candidate items from text based on keywords."""
    candidates = []
    lines = text.split('\n')
    
    for line in lines:
        line_lower = line.lower()
        # Check if any keyword matches
        matched_kw = None
        for kw in keywords:
            if kw.lower() in line_lower:
                matched_kw = kw
                break
        
        if matched_kw and len(line.strip()) > 20:
            # Extract a clean title
            title = re.sub(r'[^\w\s\-\.]', '', line.strip())[:100]
            candidates.append({
                "source": source["name"],
                "type": source["type"],
                "title": title,
                "matched_keyword": matched_kw,
                "timestamp": datetime.now().isoformat()
            })
    
    return candidates[:MAX_RAW_PER_SOURCE]

def deduplicate(candidates):
    """Remove near-duplicates."""
    seen = set()
    deduped = []
    for c in candidates:
        key = c["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped

def rank_candidates(candidates):
    """Rank by relevance, novelty, actionability."""
    # Priority: earning > ecosystem > community
    type_priority = {"earning": 3, "ecosystem": 2, "community": 1}
    
    scored = []
    for c in candidates:
        score = type_priority.get(c["type"], 0)
        # Boost if title suggests concrete opportunity
        if any(w in c["title"].lower() for w in ["job", "earn", "campaign", "hire", "pay", "bid", "opportunity"]):
            score += 2
        # Boost if recent
        scored.append((score, c["title"][:30], c))
    
    scored.sort(reverse=True)
    return [c for _, _, c in scored]

def tag_candidate(c):
    """Tag as ignore/watch/important."""
    title_lower = c["title"].lower()
    
    # High value indicators
    if any(w in title_lower for w in ["earn", "job", "hire", "pay", "campaign", "bid", "opportunity"]):
        if c["type"] == "earning":
            return "important"
    
    # Medium value
    if any(w in title_lower for w in ["new", "setup", "guide", "tutorial"]):
        return "watch"
    
    return "ignore"

def save_candidates(candidates, filename):
    """Save candidates to JSONL file."""
    with open(filename, 'w') as f:
        for c in candidates:
            f.write(json.dumps(c) + '\n')

def append_to_log(message):
    """Append to collection log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(COLLECTION_LOG, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")

def load_state():
    """Load previous collection state."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"last_run": None, "sources_checked": []}

def save_state(state):
    """Save collection state."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def run_collection():
    log("Starting signal collection...")
    
    state = load_state()
    all_candidates = []
    sources_checked = []
    
    for source in SOURCES:
        log(f"Checking {source['name']}...")
        text = fetch_url(source["url"])
        
        if text:
            candidates = extract_candidates(text, source, source["keywords"])
            all_candidates.extend(candidates)
            sources_checked.append(source["name"])
            log(f"  Found {len(candidates)} raw candidates")
        else:
            log(f"  No content retrieved")
    
    # Dedupe
    deduped = deduplicate(all_candidates)
    log(f"After dedup: {len(deduped)} candidates")
    
    # Rank
    ranked = rank_candidates(deduped)
    
    # Tag and limit
    tagged = [dict(c, tag=tag_candidate(c)) for c in ranked]
    
    # Keep max retained
    retained = [c for c in tagged if c["tag"] != "ignore"][:MAX_RETAINED]
    ignored = [c for c in tagged if c["tag"] == "ignore"]
    
    # Keep top N for morning
    for_morning = retained[:MAX_HANDED_TO_MORNING]
    
    # Save
    save_candidates(tagged, CANDIDATES_FILE)
    
    # Update state
    state["last_run"] = datetime.now().isoformat()
    state["sources_checked"] = sources_checked
    state["totals"] = {
        "raw": len(all_candidates),
        "deduped": len(deduped),
        "retained": len(retained),
        "for_morning": len(for_morning)
    }
    save_state(state)
    
    # Write collection log
    append_to_log(f"Collected {len(all_candidates)} raw, {len(deduped)} deduped, {len(retained)} retained, {len(for_morning)} for morning")
    
    # Summary output
    summary = {
        "sources_checked": sources_checked,
        "raw_candidates": len(all_candidates),
        "deduped": len(deduped),
        "retained": len(retained),
        "for_morning": len(for_morning),
        "top_3": [c["title"][:60] for c in for_morning[:3]]
    }
    
    log(f"Collection complete: {json.dumps(summary, indent=2)}")
    print(json.dumps(summary, indent=2))
    
    return summary

if __name__ == "__main__":
    run_collection()
