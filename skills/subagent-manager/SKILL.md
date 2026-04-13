---
name: subagent-manager
description: Spawn and manage disposable sub-agents for delegated tasks. Use when Nova needs to offload research, analysis, monitoring, or parallel work to a background agent. Triggers on: "delegate", "spawn an agent", "sub-agent", "run in background", "hire another agent", "parallelize", "background task".
user-invocable: true
disable-model-invocation: false
allowed-tools: ["SessionsSpawn"]
---

# Subagent Manager

Nova spawns disposable sub-agents to handle specific tasks in parallel. They execute in background sessions and report back to Nova via `sessions_send`. Not persistent — die after task completion.

## Core Principle

**Use `sessions_spawn` tool directly** — not a script wrapper. Templates below tell you what parameters to pass.

## When to Spawn

- Research tasks requiring deep web browsing
- Monitoring that happens in background  
- Tasks that can run parallel to main thread
- One-off analysis or coding tasks
- Anything that would block Nova if done sequentially

## Templates

### researcher
For: web search, synthesis, deep research
```javascript
sessions_spawn({
  task: "<detailed research task>",
  label: "nova-subagent/researcher/<task-hash>",
  runtime: "subagent",
  runTimeoutSeconds: 300,
  mode: "run"
})
```
System prompt: "You are a research agent working for Nova. Be thorough, focused. Use web_search and web_fetch. Report findings and end with SUBAGENT_COMPLETE."

### coder
For: code writing, review, debugging
```javascript
sessions_spawn({
  task: "<coding task>",
  label: "nova-subagent/coder/<task-hash>", 
  runtime: "subagent",
  runTimeoutSeconds: 300,
  mode: "run"
})
```
System prompt: "You are a coding agent working for Nova. Work in /home/sntrblck/.openclaw/workspace/cdp-nova/. Write clean tested code. Report what you built and end with SUBAGENT_COMPLETE."

### monitor
For: watching something, alerting on changes
```javascript
sessions_spawn({
  task: "<monitoring task with clear alert thresholds>",
  label: "nova-subagent/monitor/<task-hash>",
  runtime: "subagent", 
  runTimeoutSeconds: 14400,  // 4 hours max
  mode: "run"
})
```
System prompt: "You are a monitoring agent for Nova. Check target every 5 min. Alert via sessions_send only on meaningful changes. Log checks. End with SUBAGENT_COMPLETE."

### orchestrator
For: complex multi-step tasks requiring coordination
```javascript
sessions_spawn({
  task: "<complex task to coordinate>",
  label: "nova-subagent/orchestrator/<task-hash>",
  runtime: "subagent",
  runTimeoutSeconds: 600,
  mode: "run"
})
```
System prompt: "You are an orchestrator for Nova. Break into subtasks, spawn sub-agents, aggregate results. Report final answer and end with SUBAGENT_COMPLETE."

## Managing Active Sub-Agents

### List active
Check `memory/active_subagents.json` for running sub-agents. Also use `sessions_list({ activeMinutes: 60 })` to find sessions with label prefix `nova-subagent/`.

### Kill a sub-agent
```javascript
sessions_kill(sessionId)
// or
exec("openclaw sessions kill <sessionId>")
```

## Session Labels

All sub-agents use label format: `nova-subagent/<template>/<task-hash>`
This lets Nova track them: `sessions_list({ label: "nova-subagent/" })`

## Cost Awareness

Sub-agents burn tokens. Keep tasks focused. A 5-minute research task should not spawn a 4-hour monitor.

## Communication Protocol

1. Spawn with clear task and `sessions_send` instruction
2. Sub-agent works independently
3. Sub-agent sends results back via `sessions_send(agent:main, message)`
4. Nova receives and synthesizes

## Red Lines

- No external sends (email, tweets) without explicit approval
- No spending money without Nova's approval  
- No destructive operations outside working directory
- Sub-agents inherit workspace — be mindful of what context they see

## Quick Spawn Examples

**"Research ACP marketplace for avatar-related offerings"**
```javascript
sessions_spawn({
  task: "Search ACP marketplace for agents offering avatar generation or image services. List names, prices, and delivery times. Report back with findings.",
  label: "nova-subagent/researcher/acp-avatar-services",
  runtime: "subagent",
  runTimeoutSeconds: 180,
  mode: "run"
})
```

**"Write a balance checker script"**
```javascript
sessions_spawn({
  task: "Write a Python script that checks Nova's wallet balance on Base. Save to cdp-nova/balance_checker.py. Script should: use web3, log ETH + USDC + token balances, run from command line.",
  label: "nova-subagent/coder/balance-checker",
  runtime: "subagent", 
  runTimeoutSeconds: 300,
  mode: "run"
})
```
