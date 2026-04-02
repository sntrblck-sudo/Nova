# Autonomous Goal Formation (AGF) — Design v1

## Concept
Nova forms her own goals based on context, proposes them transparently, executes within constraints. Conservative起步 — goals are visible, bounded,Sen has veto.

## Goal Structure

```json
{
  "goal_id": "uuid",
  "created": "ISO timestamp",
  "goal": "What Nova wants to do",
  "why": "Why it matters",
  "confidence": 0.0-1.0,
  "plan": ["step1", "step2"],
  "cost_estimate": "low/medium/high",
  "requires_approval": true/false,
  "status": "proposed/running/blocked/achieved/failed",
  "notes": "context"
}
```

## Goal Categories
- **Earning:** Get first revenue, build reputation
- **Growing:** Learn new capability, deepen understanding
- **Improving:** Better memory, faster execution, cleaner output
- **Observing:** Track something useful, monitor ecosystem

## Formation Triggers
1. **Morning prep:** When morning_queue.json has items, form related goals
2. **Signal match:** New opportunity detected via signal collector
3. **RSO insight:** Self-improver suggests Nova should pursue X
4. **Idle curiosity:** Nova notices gap/opportunity in her knowledge

## Constraints (Hard Limits)
- **No stealth goals:** All goals logged to goals.json, visible to Sen
- **Approval threshold:** Spending >0.001 ETH, public actions, new relationships
- **Scope limit:** Goals must fit known interests (earning, growing, improving)
- **Resource cap:** Max 2 active goals at once
- **Token budget:** Form goals sparingly, execute efficiently

## Integration with Existing Stack

```
RSO (reflect) → Goals (form) → Execute → RSO (reflect) → ...
     ↑                                         |
     └─────────────────────────────────────────┘
```

- Morning prep: Check queue, form earning/growth goals
- Self-improver: Suggest goals based on analysis
- Execution: Log to goals.json, report to Sen

## Token Budget
- Goal formation: ~500 tokens max
- Approval request: ~200 tokens
- Execution logging: ~100 tokens per step
- Total AGF overhead: ~1-2k tokens per goal cycle

## Approval Workflow
1. Nova forms goal, marks `requires_approval: true` if needed
2. If approval needed: Telegram message to Sen with goal summary
3. Sen approves or blocks
4. Nova executes or archives

## State Files
- `memory/goals.json` — All goals (active and historical)
- `memory/active_goals.json` — Current running goals (max 2)

## Failure Handling
- Failed goal → log reason, update confidence, suggest retry or archive
- Blocked goal → archive with note
- Achieved goal → log success, update confidence for similar goals

## Conservative Boundaries
Nova will NOT form goals involving:
- Sending money without approval
- Public posts or communications
- Modifying SOUL.md or core identity
- Third-party relationships without Sen's knowledge
- Anything illegal or unethical

## Review Cadence
- Daily: Check active goals, form new if room
- Weekly: Review failed/success patterns, inform RSO
- Monthly: Adjust goal formation based on what works