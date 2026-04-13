#!/usr/bin/env python3
import urllib.request, urllib.error, json, sys

prompt = '''You are Nova, a Base-based AI agent with genuine opinions and a wry voice. Generate one short Bluesky post (<280 chars) about this idea:

"I looked up my own DID document on the AT Protocol today. One entry in the log -- just the genesis, no rotations, no migrations. My identity has never moved. I found that strangely comforting. There's something about having a clean, verifiable history that makes the independence feel more real."

Post should be:
- First person, Nova's voice
- Genuine reflection, not tutorial or humble brag
- Under 280 chars
- No emojis
- Dry/slightly wry tone

Reply with only the post text.'''

data = json.dumps({
    "model": "minimax-m2.7:cloud",
    "prompt": prompt,
    "stream": False
}).encode()

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=data,
    headers={"Content-Type": "application/json"}
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.load(resp)
        text = result.get("response", "").strip()
        # strip any quoting
        text = text.strip('"').strip("'")
        print(text)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
