#!/usr/bin/env python3
"""
Responsibility Contracts — Hard limits enforced by code, not prompts.
Part of the Decision Intelligence Runtime pattern.
"""

import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
CONTRACTS_DIR = MEMORY_DIR / "contracts"

CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

# Nova's operational contracts
NOVA_ID = "nova_01"
OWNER = "Sen (Senator Black)"

# Default contracts
DEFAULT_CONTRACTS = {
    "nova_wallet": {
        "agent_id": NOVA_ID,
        "role": "autonomous_agent",
        "mission": "Assist Sen, grow capabilities, operate within defined limits",
        "owner": OWNER,
        "version": "1.0.0",
        "permissions": {
            "max_tx_value_eth": 0.001,
            "max_gas_price_gwei": 200,
            "allowed_recipients": ["0x1b7eDF6F5FCAb52b680661cC82306E3DaCA7943C"],  # Sen's address
            "can_self_modify": False,
            "can_create_subagents": True
        },
        "safety_rules": {
            "require_approval_above_eth": 0.001,
            "require_approval_for_new_recipients": True,
            "max_retries_per_operation": 3,
            "abort_on_unknown_error": True
        }
    }
}

def load_contract(contract_id):
    """Load a contract by ID."""
    contract_file = CONTRACTS_DIR / f"{contract_id}.json"
    if contract_file.exists():
        with open(contract_file) as f:
            return json.load(f)
    
    # Return default if exists
    if contract_id in DEFAULT_CONTRACTS:
        return DEFAULT_CONTRACTS[contract_id]
    
    return None

def save_contract(contract_id, contract):
    """Save a contract."""
    contract_file = CONTRACTS_DIR / f"{contract_id}.json"
    with open(contract_file, 'w') as f:
        json.dump(contract, f, indent=2)

def validate_action(contract_id, action, params):
    """
    Validate an action against a contract.
    Returns: {"allowed": True/False, "rejected": None/reason, "warnings": []}
    """
    contract = load_contract(contract_id)
    
    if not contract:
        return {"allowed": False, "rejected": "contract_not_found", "warnings": []}
    
    rejected = None
    warnings = []
    
    # Check tx value
    if action == "send_tx":
        value_eth = params.get("value_eth", 0)
        max_value = contract["permissions"]["max_tx_value_eth"]
        
        if value_eth > max_value:
            rejected = f"tx_value_exceeds_limit ({value_eth} ETH > {max_value} ETH)"
        elif value_eth > contract["safety_rules"]["require_approval_above_eth"]:
            warnings.append(f"value_above_approval_threshold ({value_eth} ETH)")
        
        # Check recipient
        recipient = params.get("recipient", "").lower()
        allowed = [r.lower() for r in contract["permissions"]["allowed_recipients"]]
        if recipient not in allowed:
            if contract["safety_rules"]["require_approval_for_new_recipients"]:
                rejected = f"recipient_not_whitelisted ({recipient})"
            else:
                warnings.append(f"new_recipient_not_in_whitelist ({recipient})")
        
        # Check gas price
        gas_price = params.get("gas_price_gwei", 0)
        max_gas = contract["permissions"]["max_gas_price_gwei"]
        if gas_price > max_gas:
            warnings.append(f"gas_price_high ({gas_price} gwei > {max_gas} gwei)")
    
    # Check self-modification
    if action == "self_modify":
        if not contract["permissions"]["can_self_modify"]:
            rejected = "self_modification_not_allowed"
    
    return {
        "allowed": rejected is None,
        "rejected": rejected,
        "warnings": warnings,
        "contract_id": contract_id,
        "action": action,
        "validated_at": datetime.now().isoformat()
    }

def create_policy_proposal(contract_id, policy_type, params, reasoning="", confidence=0.5):
    """Create a structured policy proposal (Pillar #1)."""
    proposal = {
        "dfid": f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{policy_type}",
        "agent_id": NOVA_ID,
        "policy_kind": policy_type,
        "params": params,
        "reasoning": reasoning,
        "confidence_score": confidence,
        "created_at": datetime.now().isoformat()
    }
    
    # Validate against contract
    action_map = {
        "SEND_TX": "send_tx",
        "SELF_MODIFY": "self_modify",
        "CREATE_SUBAGENT": "create_subagent"
    }
    
    action = action_map.get(policy_type, policy_type.lower())
    validation = validate_action(contract_id, action, params)
    
    proposal["validation"] = validation
    
    if not validation["allowed"]:
        proposal["final_decision"] = "REJECTED"
    elif validation["warnings"]:
        proposal["final_decision"] = "APPROVED_WITH_WARNINGS"
    else:
        proposal["final_decision"] = "APPROVED"
    
    return proposal

def list_contracts():
    """List all contracts."""
    contracts = []
    for f in CONTRACTS_DIR.glob("*.json"):
        with open(f) as fp:
            c = json.load(fp)
            contracts.append({
                "id": f.stem,
                "version": c.get("version"),
                "permissions": c.get("permissions")
            })
    return contracts

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: contracts.py <command> [args]")
        print("Commands: validate, propose, list, save")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "validate" and len(sys.argv) >= 5:
        result = validate_action(sys.argv[2], sys.argv[3], json.loads(sys.argv[4]))
        print(json.dumps(result, indent=2))
    
    elif cmd == "propose" and len(sys.argv) >= 5:
        policy_type = sys.argv[2]
        params = json.loads(sys.argv[3])
        reasoning = sys.argv[4] if len(sys.argv) > 4 else ""
        proposal = create_policy_proposal("nova_wallet", policy_type, params, reasoning)
        print(json.dumps(proposal, indent=2))
    
    elif cmd == "list":
        contracts = list_contracts()
        print(f"Contracts: {len(contracts)}")
        for c in contracts:
            print(f"  {c['id']} (v{c['version']})")
    
    elif cmd == "save":
        # Save default contracts
        for cid, contract in DEFAULT_CONTRACTS.items():
            save_contract(cid, contract)
            print(f"Saved contract: {cid}")
    
    else:
        print("Invalid command")