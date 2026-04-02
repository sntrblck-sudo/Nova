#!/usr/bin/env python3
"""
Preference Selection Layer — Low-risk choices guided by preference.
Preference may shape framing and selection, but may not override reality, safety, or operator intent.
"""

import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
PREFERENCES_FILE = MEMORY_DIR / "preferences.json"

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def set_preference(domain, preference_key, value, reason="", source="experience"):
    """
    Set a preference for a domain.
    
    domain: what area (surfacing, naming, framing, structure, tagging)
    preference_key: what aspect (tone, format, threshold, etc.)
    value: the preferred value
    reason: why this is preferred
    source: how this was learned (experience, heuristic, identity)
    """
    data = load_json(PREFERENCES_FILE)
    if "preferences" not in data:
        data["preferences"] = []
    
    # Check if exists
    found = False
    for p in data["preferences"]:
        if p["domain"] == domain and p["key"] == preference_key:
            p["value"] = value
            p["reason"] = reason
            p["updated_at"] = datetime.now().isoformat()
            p["confidence"] = min(0.99, p.get("confidence", 0.5) + 0.05)
            found = True
            break
    
    if not found:
        data["preferences"].append({
            "domain": domain,
            "key": preference_key,
            "value": value,
            "reason": reason,
            "source": source,
            "confidence": 0.5,
            "times_used": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
    
    save_json(PREFERENCES_FILE, data)
    return {"set": True, "domain": domain, "key": preference_key, "value": value}

def get_preference(domain, preference_key, default=None):
    """Get a specific preference."""
    data = load_json(PREFERENCES_FILE)
    
    for p in data.get("preferences", []):
        if p["domain"] == domain and p["key"] == preference_key:
            # Track usage
            p["times_used"] += 1
            save_json(PREFERENCES_FILE, data)
            return p["value"]
    
    return default

def get_domain_preferences(domain):
    """Get all preferences for a domain."""
    data = load_json(PREFERENCES_FILE)
    return [p for p in data.get("preferences", []) if p["domain"] == domain]

def choose(preference_domain, options, context=None):
    """
    Make a low-risk choice guided by preference.
    
    preference_domain: what kind of choice (surfacing_format, naming, tagging, etc.)
    options: list of options to choose between
    context: additional context for the choice
    
    Returns: {chosen: option, reasoning: str, confidence: float}
    """
    context = context or {}
    
    # Get preference for this domain
    pref_value = get_preference(preference_domain, "preferred_style", None)
    
    if pref_value is None:
        # No preference yet, return first option
        return {
            "chosen": options[0] if options else None,
            "reasoning": "no_preference_yet",
            "confidence": 0.3
        }
    
    # Apply preference
    chosen = None
    reasoning = f"matches_preference:{pref_value}"
    confidence = 0.7
    
    # Simple matching logic
    for option in options:
        if pref_value in str(option).lower():
            chosen = option
            confidence = 0.8
            break
    
    if chosen is None:
        # Preference didn't match, default to first
        chosen = options[0]
        reasoning = "preference_not_matched"
        confidence = 0.4
    
    return {
        "chosen": chosen,
        "reasoning": reasoning,
        "confidence": confidence,
        "preference_used": pref_value
    }

def choose_structure(available_formats, content_type="summary"):
    """
    Choose how to structure something based on preference.
    
    allowed: summary, brief, detailed, bullet, narrative
    """
    pref = get_preference("structure", content_type, "summary")
    
    # Verify it's in available formats
    if pref in available_formats:
        return {"format": pref, "source": "preference"}
    
    # Default
    return {"format": available_formats[0], "source": "default"}

def choose_label(candidates, context=None):
    """
    Choose which internal label to apply based on preference.
    
    Returns the chosen label and reasoning.
    """
    context = context or {}
    
    # Get preferred label style
    pref = get_preference("labeling", "preferred_style", "neutral")
    
    # Score candidates
    scored = []
    for candidate in candidates:
        score = 0.5
        if pref in candidate.lower():
            score = 0.8
        scored.append((candidate, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    chosen, confidence = scored[0]
    
    return {
        "chosen": chosen,
        "confidence": confidence,
        "preference": pref
    }

def should_save(item_type, item_content, metadata=None):
    """
    Decide whether to save something based on preference.
    
    Returns: {save: bool, reason: str, confidence: float}
    """
    context = metadata or {}
    
    # Get save threshold preference
    threshold = get_preference("saving", "significance_threshold", 0.5)
    
    # Simple heuristic: compressible + novel = save
    compressibility = estimate_compressibility(item_content)
    novelty = estimate_novelty(item_content)
    
    score = (compressibility * 0.6) + (novelty * 0.4)
    
    if score >= threshold:
        return {
            "save": True,
            "reason": f"compressibility:{compressibility:.2f}+novelty:{novelty:.2f}>{threshold}",
            "confidence": score
        }
    else:
        return {
            "save": False,
            "reason": f"score:{score:.2f}<threshold:{threshold}",
            "confidence": score
        }

def estimate_compressibility(text):
    """Estimate how compressible (pattern-like) text is."""
    if not text:
        return 0.0
    
    # Simple heuristic: shorter with clear structure = more compressible
    words = text.split()
    unique_ratio = len(set(words)) / len(words) if words else 1
    
    # High unique ratio = lots of different words = less pattern-like
    return 1.0 - unique_ratio

def estimate_novelty(text):
    """Estimate how novel this content is vs existing knowledge."""
    # This is simplified - would need to check against existing memories
    # For now, assume some novelty
    return 0.5

def choose_promotion(item, target_queue="watchlist", reason=""):
    """
    Decide whether to promote an item from note to watchlist, or weak signal to pattern.
    
    Returns: {promote: bool, target: str, confidence: float}
    """
    # Check preference for promotion aggressiveness
    pref = get_preference("promotion", "threshold", "moderate")
    
    thresholds = {
        "conservative": 0.8,
        "moderate": 0.6,
        "aggressive": 0.4
    }
    
    threshold = thresholds.get(pref, 0.6)
    
    # Estimate item strength
    strength = estimate_item_strength(item)
    
    if strength >= threshold:
        return {
            "promote": True,
            "target": target_queue,
            "confidence": strength,
            "reason": reason
        }
    else:
        return {
            "promote": False,
            "target": None,
            "confidence": strength,
            "reason": f"strength:{strength:.2f}<threshold:{threshold}"
        }

def estimate_item_strength(item):
    """Estimate how strong/promising an item is."""
    score = 0.5
    
    if isinstance(item, dict):
        if item.get("repeat_count", 0) >= 3:
            score += 0.2
        if item.get("severity") in ["warning", "critical"]:
            score += 0.2
    
    return min(1.0, score)

def get_stats():
    """Get preference statistics."""
    data = load_json(PREFERENCES_FILE)
    prefs = data.get("preferences", [])
    
    by_domain = {}
    for p in prefs:
        domain = p["domain"]
        if domain not in by_domain:
            by_domain[domain] = 0
        by_domain[domain] += 1
    
    return {
        "total_preferences": len(prefs),
        "by_domain": by_domain,
        "most_used": max(prefs, key=lambda x: x.get("times_used", 0))["key"] if prefs else None
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: preferences.py <command> [args]")
        print("Commands: set, get, choose, stats")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "set" and len(sys.argv) >= 5:
        domain = sys.argv[2]
        key = sys.argv[3]
        value = sys.argv[4]
        reason = sys.argv[5] if len(sys.argv) > 5 else ""
        result = set_preference(domain, key, value, reason)
        print(json.dumps(result, indent=2))
    
    elif cmd == "get" and len(sys.argv) >= 4:
        domain = sys.argv[2]
        key = sys.argv[3]
        value = get_preference(domain, key, "no_preference")
        print(f"{domain}.{key} = {value}")
    
    elif cmd == "choose" and len(sys.argv) >= 3:
        options = sys.argv[3].split(",")
        result = choose("general", options)
        print(json.dumps(result, indent=2))
    
    elif cmd == "stats":
        print(json.dumps(get_stats(), indent=2))
    
    elif cmd == "test":
        # Set some preferences
        set_preference("surfacing", "tone", "concise", "Sen prefers brief messages")
        set_preference("structure", "summary", "bullet", "Bullet points work better")
        set_preference("saving", "significance_threshold", 0.6, "Save things with reasonable novelty")
        
        # Test choosing
        result = choose("surfacing", ["concise", "detailed", "narrative"])
        print(f"Chosen: {result}")
        
        result = should_save("test", "This is a test note with some content")
        print(f"Should save: {result}")
    
    else:
        print("Invalid command")