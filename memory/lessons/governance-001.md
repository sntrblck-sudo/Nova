# Governance Pattern: Pre-Execution Intent Classification
**Added:** 2026-04-13
**Source:** Governance-as-Infrastructure brief, Microsoft Agent Governance Toolkit

## Lesson
Pattern_sentinel currently logs patterns after execution. The governance-as-infrastructure model requires intent classification BEFORE execution. This is the difference between auditing and governing.

## Risk Exposure (from brief)
- Goal hijacking: prompt injection into task queue
- Memory poisoning: SQLite lesson store manipulation
- Rogue agent behavior: unconstrained self_improver_v2 execution
- Credential abuse: API key scope
- Data exfiltration: outbound file/network actions

## Action Items
- [ ] Evaluate pattern_sentinel for pre-execution intent classification
- [ ] Assess Microsoft Agent Governance Toolkit (PyPI) for OpenClaw compatibility
- [ ] Add outbound data flow visibility (what left the system, not just what ran)
- [ ] Review ClawHub supply chain risk with Ed25519 manifest verification pattern
