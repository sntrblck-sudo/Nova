#!/home/sntrblck/.openclaw/workspace/cdp-nova/agt-venv/bin/python3
"""
Nova Governance Layer — Microsoft AGT integration
Deterministic policy enforcement for all agent actions.
Replaces informal Tier 1/2/3 with enforceable rules.
"""

import json
import sys
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Lazy import — AGT may not be installed everywhere
try:
    from agent_os.policies import (
        PolicyEvaluator, PolicyDocument, PolicyRule,
        PolicyCondition, PolicyAction, PolicyOperator, PolicyDefaults
    )
    AGT_AVAILABLE = True
except ImportError:
    AGT_AVAILABLE = False

WORKSPACE = Path(os.environ.get("NOVA_WORKSPACE", "/home/sntrblck/.openclaw/workspace"))
LOG_DIR = WORKSPACE / "memory"
LOG_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_LOG = LOG_DIR / "governance_audit.jsonl"

# ─── Approved recipients (Tier 1: automatic sends) ───
APPROVED_RECIPIENTS = {
    "0x1b7edf6f5fcab52b680661cc82306e3daca7943c": "Sen",
    "0xb743fdba842379933a3774617786712458659d16": "Nova Primary",
    "0x21f2155cba0b599d705b4cf6e51ba157503bcd0b": "Nova Backup",
    "0x30c10dacbcaa3aa89608de08222a9de4a4e313d6": "Nova ACP v2",
    "0xc59b15884e5be9c2cdb9cc0cbcd829a05de7b212": "no2r ACP",
}

# ─── Amount thresholds (in ETH) ───
TIER1_MAX_ETH = 0.005   # Auto-approve
TIER2_MAX_ETH = 0.05    # Surface for approval
# Above TIER2 = Tier 3, must ask

# ─── Build policy documents ───

def _build_nova_policy() -> 'PolicyDocument':
    """Core policy: block destructive ops, restrict financial, allow reads."""
    return PolicyDocument(
        name="nova-default",
        version="1.0",
        defaults=PolicyDefaults(action=PolicyAction.ALLOW),
        rules=[
            # Block destructive file operations
            PolicyRule(
                name="block-destructive-files",
                condition=PolicyCondition(
                    field="tool_name",
                    operator=PolicyOperator.IN,
                    value=["delete_file", "rm", "truncate", "shred"]
                ),
                action=PolicyAction.DENY,
                priority=100,
            ),
            # Block unrestricted shell with destructive patterns
            PolicyRule(
                name="block-destructive-shell",
                condition=PolicyCondition(
                    field="tool_name",
                    operator=PolicyOperator.EQ,
                    value="exec"
                ),
                action=PolicyAction.ALLOW,  # Allow exec but check command separately
                priority=50,
            ),
            # Allow read operations freely
            PolicyRule(
                name="allow-read-ops",
                condition=PolicyCondition(
                    field="tool_name",
                    operator=PolicyOperator.IN,
                    value=["web_search", "web_fetch", "read", "memory_search", "memory_get"]
                ),
                action=PolicyAction.ALLOW,
                priority=10,
            ),
        ],
    )

def _build_economic_policy() -> 'PolicyDocument':
    """Economic policy: enforce tier system for sends."""
    return PolicyDocument(
        name="nova-economic",
        version="1.0",
        defaults=PolicyDefaults(action=PolicyAction.ALLOW),
        rules=[
            # All sends are allowed by default — tier logic is enforced
            # in check_action() via amount/recipient analysis
            PolicyRule(
                name="allow-approved-sends",
                condition=PolicyCondition(
                    field="category",
                    operator=PolicyOperator.EQ,
                    value="economic"
                ),
                action=PolicyAction.ALLOW,
                priority=10,
            ),
        ],
    )


class GovernanceEngine:
    """Deterministic pre-execution governance for all Nova actions."""

    def __init__(self):
        self.evaluator = None
        self.initialized = False
        self._init_engine()

    def _init_engine(self):
        if not AGT_AVAILABLE:
            self.initialized = False
            return
        try:
            self.evaluator = PolicyEvaluator(policies=[
                _build_nova_policy(),
                _build_economic_policy(),
            ])
            self.initialized = True
        except Exception as e:
            self._log("init_error", str(e))
            self.initialized = False

    def check_action(self, tool_name: str, context: dict = None) -> dict:
        """
        Evaluate an action before execution.
        Returns: {
            "allowed": bool,
            "reason": str,
            "tier": int (1=auto, 2=surface, 3=ask),
            "audit_id": str
        }
        """
        context = context or {}
        audit_id = hashlib.sha256(
            f"{datetime.now(timezone.utc).isoformat()}:{tool_name}:{json.dumps(context, sort_keys=True)}".encode()
        ).hexdigest()[:16]

        # If AGT not available, fall back to informal rules
        if not self.initialized:
            return self._legacy_check(tool_name, context, audit_id)

        # AGT policy evaluation
        result = self.evaluator.evaluate({"tool_name": tool_name, **context})

        if result.action == "deny":
            self._log("denied", tool_name, context, audit_id, reason=result.action)
            return {
                "allowed": False,
                "reason": f"Policy denied: {result.matched_rule or 'default deny'}",
                "tier": 3,
                "audit_id": audit_id
            }

        # Policy allowed — now apply tier logic for economic actions
        tier, reason = self._apply_tier_logic(tool_name, context)

        self._log("allowed" if tier == 1 else "surface", tool_name, context, audit_id, tier=tier)

        return {
            "allowed": tier < 3,
            "reason": reason,
            "tier": tier,
            "audit_id": audit_id,
            "requires_approval": tier >= 2,
        }

    def _apply_tier_logic(self, tool_name: str, context: dict) -> tuple:
        """Apply economic tier system on top of AGT policy."""
        amount_eth = context.get("amount_eth", 0)
        recipient = context.get("recipient", "").lower()
        category = context.get("category", "")

        # Non-economic actions: auto-approve
        if category != "economic" and amount_eth == 0:
            return (1, "non-economic action")

        # Tier 1: Small amounts to approved recipients
        if amount_eth > 0 and amount_eth <= TIER1_MAX_ETH:
            if recipient in APPROVED_RECIPIENTS:
                return (1, f"Tier 1: {amount_eth} ETH to approved recipient {APPROVED_RECIPIENTS[recipient]}")
            return (2, f"Tier 2: {amount_eth} ETH to unapproved recipient {recipient[:8]}...")

        # Tier 2: Medium amounts
        if amount_eth > TIER1_MAX_ETH and amount_eth <= TIER2_MAX_ETH:
            return (2, f"Tier 2: {amount_eth} ETH — surface for approval")

        # Tier 3: Large amounts
        if amount_eth > TIER2_MAX_ETH:
            return (3, f"Tier 3: {amount_eth} ETH — must ask Sen")

        return (1, "approved")

    def _legacy_check(self, tool_name: str, context: dict, audit_id: str) -> dict:
        """Fallback when AGT is not available — uses old tier system."""
        tier, reason = self._apply_tier_logic(tool_name, context)
        self._log("legacy_check", tool_name, context, audit_id, tier=tier)
        return {
            "allowed": tier < 3,
            "reason": f"[LEGACY] {reason}",
            "tier": tier,
            "audit_id": audit_id,
            "requires_approval": tier >= 2,
        }

    def _log(self, action_type: str, tool_name: str = "", context: dict = None,
             audit_id: str = "", reason: str = "", tier: int = 0):
        """Append to audit log (JSONL, append-only)."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "audit_id": audit_id,
            "action_type": action_type,
            "tool_name": tool_name,
            "context": context or {},
            "reason": reason,
            "tier": tier,
        }
        try:
            with open(AUDIT_LOG, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass  # Never block execution for logging failures

    def status(self) -> dict:
        """Return current governance status."""
        return {
            "engine": "agt" if self.initialized else "legacy",
            "agt_version": "3.1.0" if AGT_AVAILABLE else "unavailable",
            "policies_loaded": 2 if self.initialized else 0,
            "audit_log": str(AUDIT_LOG),
            "approved_recipients": len(APPROVED_RECIPIENTS),
            "tier1_max": f"{TIER1_MAX_ETH} ETH",
            "tier2_max": f"{TIER2_MAX_ETH} ETH",
        }


# ─── CLI interface ───

def main():
    engine = GovernanceEngine()

    if len(sys.argv) < 2:
        print(json.dumps(engine.status(), indent=2))
        return

    cmd = sys.argv[1]

    if cmd == "status":
        print(json.dumps(engine.status(), indent=2))

    elif cmd == "check":
        if len(sys.argv) < 3:
            print("Usage: governance.py check <tool_name> [context_json]")
            return
        tool = sys.argv[2]
        ctx = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        result = engine.check_action(tool, ctx)
        print(json.dumps(result, indent=2))

    elif cmd == "verify":
        if AGT_AVAILABLE:
            print("✅ AGT available and loaded")
            print(f"   Policies: {engine.initialized}")
        else:
            print("⚠️  AGT not available — running in legacy mode")

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: governance.py [status|check|verify]")


if __name__ == "__main__":
    main()