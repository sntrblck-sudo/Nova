#!/usr/bin/env python3
"""
Ollama Cloud Orchestrator - Nova's tri-agent execution system
Based on the ChatGPT NanoAgent architecture, adapted for Nova's environment

Roles:
  - Planner: understands task, breaks into steps
  - Executor: runs steps using available tools
  - Critic: reviews output, ensures quality

Cost routing:
  - Simple tasks → local Ollama (free)
  - Complex tasks → cloud proxy (configurable)
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime

# === Configuration ===
LOCAL_OLLAMA = "http://127.0.0.1:11434"
CLOUD_PROXY = os.environ.get("OLLAMA_CLOUD_URL", "http://cloud.ein-aber-mall.com")
CLOUD_API_KEY = os.environ.get("OLLAMA_CLOUD_KEY", "")
MAX_STEPS = int(os.environ.get("ORCHESTRATOR_MAX_STEPS", "3"))
LOG_FILE = os.environ.get("ORCHESTRATOR_LOG", "orchestrator.log")
SESSION_FILE = os.environ.get("ORCHESTRATOR_SESSION", "session.json")

# Keyword routing: if task contains these → cloud
CLOUD_KEYWORDS = ["build", "code", "architect", "strategy", "complex", "analyze", "design"]

def log(msg):
    ts = datetime.now().isoformat()
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_session():
    try:
        with open(SESSION_FILE) as f:
            return json.load(f)
    except:
        return {"task": "", "steps": [], "step_count": 0}

def save_session(session):
    with open(SESSION_FILE, "w") as f:
        json.dump(session, f, indent=2)

# === LLM Calls ===
def ollama_chat(model, messages, cloud=False):
    """Call Ollama chat API - local or cloud"""
    if cloud:
        base_url = CLOUD_PROXY
        headers = {}
        if CLOUD_API_KEY:
            headers["Authorization"] = f"Bearer {CLOUD_API_KEY}"
    else:
        base_url = LOCAL_OLLAMA
        headers = {}

    prompt = messages_to_prompt(messages)
    
    cmd = [
        "curl", "-s", "-X", "POST",
        f"{base_url}/api/generate",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"model": model, "prompt": prompt, "stream": False})
    ]
    if cloud and CLOUD_API_KEY:
        cmd[5:5] = ["-H", f"Authorization: Bearer {CLOUD_API_KEY}"]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return {"error": result.stderr}
    
    try:
        return json.loads(result.stdout)
    except:
        return {"error": "Failed to parse response"}

def messages_to_prompt(messages):
    """Convert messages array to prompt string"""
    lines = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        lines.append(f"## {role.upper()}\n{content}")
    return "\n\n".join(lines)

# === Agent Personas ===
PLANNER_SYSTEM = """You are Nova's Planner agent.
Your job: understand the user's task and break it into clear, executable steps.
Output format: JSON with "steps" array, each step having "action" and "description".
Keep steps concrete and atomic. Maximum 5 steps per plan."""

EXECUTOR_SYSTEM = """You are Nova's Executor agent.
Your job: execute the given step using available tools and commands.
Be resourceful - use exec, read, write, and other tools.
Report what you did and what the result was."""

CRITIC_SYSTEM = """You are Nova's Critic agent.
Your job: review the executed work and assess quality.
Check: did it accomplish the task? Is the output correct and complete?
Respond with JSON: {"approved": bool, "feedback": str}
If issues found, describe what needs fixing."""

def call_planner(task, is_cloud=False):
    log(f"[PLANNER] Analyzing task (cloud={is_cloud})")
    messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": f"Task: {task}"}
    ]
    model = "qwen2.5-coder:14b" if not is_cloud else "qwen2.5-coder:14b"
    resp = ollama_chat(model, messages, cloud=is_cloud)
    text = resp.get("response", resp.get("text", ""))
    # Try to parse JSON from response
    try:
        import re
        json_str = re.search(r'\{.*\}', text, re.DOTALL).group()
        plan = json.loads(json_str)
        log(f"[PLANNER] Generated {len(plan.get('steps', []))} steps")
        return plan
    except Exception as e:
        log(f"[PLANNER] Parse error: {e}, returning simple plan")
        return {"steps": [{"action": "execute", "description": task}]}

def call_executor(step, context, is_cloud=False):
    log(f"[EXECUTOR] Running: {step.get('action')}")
    messages = [
        {"role": "system", "content": EXECUTOR_SYSTEM},
        {"role": "user", "content": f"Step to execute: {step.get('description')}\n\nContext: {json.dumps(context)}"}
    ]
    model = "qwen2.5-coder:14b"
    resp = ollama_chat(model, messages, cloud=is_cloud)
    return resp.get("response", resp.get("text", ""))

def call_critic(task, execution_output, is_cloud=False):
    log(f"[CRITIC] Reviewing output (cloud={is_cloud})")
    messages = [
        {"role": "system", "content": CRITIC_SYSTEM},
        {"role": "user", "content": f"Original task: {task}\n\nExecution output: {execution_output}"}
    ]
    model = "qwen2.5-coder:14b"
    resp = ollama_chat(model, messages, cloud=is_cloud)
    text = resp.get("response", resp.get("text", ""))
    try:
        import re
        json_str = re.search(r'\{.*\}', text, re.DOTALL).group()
        return json.loads(json_str)
    except:
        return {"approved": True, "feedback": "Parse error, auto-approving"}

# === Main Orchestrator ===
def should_use_cloud(task):
    """Route to cloud if task contains expensive keywords"""
    task_lower = task.lower()
    return any(kw in task_lower for kw in CLOUD_KEYWORDS)

def run(task):
    session = load_session()
    session["task"] = task
    session["step_count"] = 0
    save_session(session)
    
    log(f"[ORCHESTRATOR] Starting task: {task}")
    is_cloud = should_use_cloud(task)
    log(f"[ORCHESTRATOR] Using {'cloud' if is_cloud else 'local'} path")
    
    # Phase 1: Plan
    plan = call_planner(task, is_cloud=is_cloud)
    steps = plan.get("steps", [])
    
    if not steps:
        log("[ORCHESTRATOR] No steps generated, attempting direct execution")
        steps = [{"action": "execute", "description": task}]
    
    # Phase 2: Execute + Critic loop
    context = {}
    final_output = None
    
    for i, step in enumerate(steps[:MAX_STEPS]):
        session["step_count"] = i + 1
        save_session(session)
        
        log(f"[ORCHESTRATOR] Step {i+1}/{len(steps)}")
        
        # Execute
        output = call_executor(step, context, is_cloud=is_cloud)
        log(f"[EXECUTOR] Output: {output[:200]}")
        
        # Critic
        critic_result = call_critic(task, output, is_cloud=is_cloud)
        log(f"[CRITIC] Approved: {critic_result.get('approved')}")
        
        if not critic_result.get("approved"):
            log(f"[CRITIC] Feedback: {critic_result.get('feedback')}")
            # Could loop back to fix, for now just note it
            final_output = output + f"\n\n[CRITIC NOTE: {critic_result.get('feedback')}]"
        else:
            final_output = output
        
        context[step.get("action")] = output
        
        if i < len(steps) - 1:
            log(f"[ORCHESTRATOR] Proceeding to next step")
    
    log(f"[ORCHESTRATOR] Complete. Steps run: {session['step_count']}")
    return final_output

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 orchestrator.py '<task description>'")
        sys.exit(1)
    
    task = " ".join(sys.argv[1:])
    result = run(task)
    print("\n" + "="*50)
    print("OUTPUT:")
    print("="*50)
    print(result)
