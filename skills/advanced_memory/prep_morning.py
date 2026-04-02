#!/usr/bin/env python3
"""
Nova Pre-Morning Prep - Component D
Transforms signal candidates into ranked morning input.
Run after collection, before morning cron.
"""

import json
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
CANDIDATES_FILE = LOG_DIR / "signal_candidates.jsonl"
MORNING_QUEUE = LOG_DIR / "morning_queue.json"
MORNING_RANKED = LOG_DIR / "morning_ranked.md"

MAX_QUEUE_ITEMS = 5

def log(msg):
    print(f"[prep] {msg}")

def load_candidates():
    """Load candidates from JSONL."""
    candidates = []
    if not CANDIDATES_FILE.exists():
        log("No candidates file found")
        return candidates
    
    with open(CANDIDATES_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    candidates.append(json.loads(line))
                except:
                    pass
    return candidates

def deduplicate_near(lst):
    """Remove near-duplicates by title similarity."""
    seen = set()
    deduped = []
    for c in lst:
        key = c.get("title", "")[:40].lower().strip()
        if key not in seen and len(key) > 10:
            seen.add(key)
            deduped.append(c)
    return deduped

def filter_stale(candidates, max_age_hours=24):
    """Remove items older than max_age_hours."""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    filtered = []
    for c in candidates:
        try:
            ts = datetime.fromisoformat(c.get("timestamp", "2000-01-01"))
            if ts > cutoff:
                filtered.append(c)
        except:
            filtered.append(c)  # Keep if can't parse
    return filtered

def drop_low_confidence(candidates):
    """Drop items tagged ignore."""
    return [c for c in candidates if c.get("tag", "ignore") != "ignore"]

def rank_for_morning(candidates):
    """
    Rank by:
    1. importance (tag)
    2. relevance to earning
    3. actionability
    """
    tag_priority = {"important": 3, "watch": 2, "ignore": 0}
    
    scored = []
    for c in candidates:
        score = tag_priority.get(c.get("tag", "ignore"), 0)
        
        # Boost for earning type
        if c.get("type") == "earning":
            score += 2
        
        # Boost for actionable keywords
        title = c.get("title", "").lower()
        if any(w in title for w in ["earn", "job", "hire", "pay", "campaign", "bid", "register", "sign up"]):
            score += 2
        
        # Penalty for meta tags / HTML noise
        if any(w in title for w in ["title", "meta", "property", "content", "http"]):
            score -= 5
        
        scored.append((score, c.get("title", "")[:30], c))
    
    scored.sort(reverse=True)
    return [c for _, _, c in scored]

def build_why_matters(c):
    """Build a one-line why-it-matters note."""
    tag = c.get("tag", "watch")
    source = c.get("source", "unknown")
    title = c.get("title", "")[:60]
    
    if tag == "important" and c.get("type") == "earning":
        return f"Direct earning opportunity from {source}"
    elif tag == "important":
        return f"Important update from {source}: {title}"
    else:
        return f"Potentially useful: {title}"

def build_morning_item(c, rank):
    """Build a structured morning queue item."""
    return {
        "rank": rank,
        "source": c.get("source"),
        "type": c.get("type"),
        "tag": c.get("tag"),
        "title": c.get("title", "")[:100],
        "why_matters": build_why_matters(c),
        "actionability": "high" if c.get("tag") == "important" else "medium",
        "needs_human_review": c.get("tag") == "important"
    }

def save_queue(queue):
    """Save morning queue JSON."""
    with open(MORNING_QUEUE, 'w') as f:
        json.dump(queue, f, indent=2)

def save_ranked_markdown(queue):
    """Save morning ranked as markdown for easy reading."""
    with open(MORNING_RANKED, 'w') as f:
        f.write(f"# Morning Queue — {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write(f"Items ranked by relevance, importance, and actionability.\n\n")
        
        if not queue:
            f.write("No high-priority items today.\n")
            return
        
        f.write("## Top Items\n\n")
        for item in queue:
            emoji = "🔴" if item["needs_human_review"] else "🟡" if item["actionability"] == "high" else "🟢"
            f.write(f"{emoji} **{item['rank']}. {item['source']}** ({item['type']})\n")
            f.write(f"   {item['title']}\n")
            f.write(f"   → {item['why_matters']}\n")
            if item["needs_human_review"]:
                f.write(f"   ⚠️ **Needs human review**\n")
            f.write("\n")

def run_prep():
    log("Starting pre-morning prep...")
    
    # Load
    candidates = load_candidates()
    log(f"Loaded {len(candidates)} candidates")
    
    if not candidates:
        log("No candidates - creating empty queue")
        save_queue({"timestamp": datetime.now().isoformat(), "items": [], "count": 0})
        save_ranked_markdown([])
        return
    
    # Filter pipeline
    filtered = deduplicate_near(candidates)
    log(f"After dedup near: {len(filtered)}")
    
    filtered = filter_stale(filtered)
    log(f"After stale filter: {len(filtered)}")
    
    filtered = drop_low_confidence(filtered)
    log(f"After low-confidence drop: {len(filtered)}")
    
    # Rank
    ranked = rank_for_morning(filtered)
    log(f"Ranked: {len(ranked)} items")
    
    # Take top N
    top = ranked[:MAX_QUEUE_ITEMS]
    
    # Build structured items
    queue_items = []
    for i, c in enumerate(top):
        item = build_morning_item(c, i + 1)
        queue_items.append(item)
    
    # Save
    queue = {
        "timestamp": datetime.now().isoformat(),
        "count": len(queue_items),
        "items": queue_items
    }
    save_queue(queue)
    
    save_ranked_markdown(queue_items)
    
    log(f"Prep complete. Queue: {len(queue_items)} items")
    print(json.dumps(queue, indent=2))
    
    return queue

if __name__ == "__main__":
    run_prep()
