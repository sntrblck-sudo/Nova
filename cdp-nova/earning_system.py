"""
Nova's Earning System
====================
Manages Nova's revenue streams, opportunities, and payment receiving.

Earning Categories:
- Passive: Incoming transfers, staking rewards, token appreciation
- Active: Services rendered, value provided, commissions

Revenue Tracking:
- All incoming payments logged
- Opportunities tracked
- Service agreements recorded
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from enum import Enum

EARNINGS_LOG = Path("/home/sntrblck/.openclaw/workspace/memory/earnings_log.jsonl")
OPPORTUNITIES_FILE = Path("/home/sntrblck/.openclaw/workspace/memory/opportunities.json")
SERVICES_FILE = Path("/home/sntrblck/.openclaw/workspace/memory/services.json")


class EarningType(Enum):
    INCOMING_TRANSFER = "incoming_transfer"
    SERVICE_PAYMENT = "service_payment"
    STAKING_REWARD = "staking_reward"
    TOKEN_REWARD = "token_reward"
    REFERRAL = "referral"
    OTHER = "other"


class OpportunityStatus(Enum):
    IDENTIFIED = "identified"
    INTERESTED = "interested"
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    AGREED = "agreed"
    COMPLETED = "completed"
    PASSED = "passed"
    FAILED = "failed"


@dataclass
class Earning:
    type: str
    amount_eth: float
    from_address: str
    description: str
    tx_hash: Optional[str] = None
    timestamp: Optional[float] = None
    service_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self):
        return {
            "type": self.type,
            "amount_eth": self.amount_eth,
            "from_address": self.from_address,
            "description": self.description,
            "tx_hash": self.tx_hash,
            "timestamp": self.timestamp,
            "service_id": self.service_id,
        }


@dataclass
class Opportunity:
    id: str
    source: str  # where discovered
    description: str
    potential_eth: float
    effort: str  # low/medium/high
    status: str
    notes: str
    discovered_at: float
    updated_at: float

    def to_dict(self):
        return asdict(self)


def log_earning(earning: Earning):
    """Log an earning event"""
    EARNINGS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(EARNINGS_LOG, "a") as f:
        f.write(json.dumps(earning.to_dict()) + "\n")


def get_total_earnings(limit: Optional[int] = None) -> dict:
    """Get total earnings summary"""
    if not EARNINGS_LOG.exists():
        return {"total_eth": 0, "count": 0, "by_type": {}}

    earnings = []
    with open(EARNINGS_LOG) as f:
        for line in f:
            earnings.append(json.loads(line))

    if limit:
        earnings = earnings[-limit:]

    total = sum(e["amount_eth"] for e in earnings)
    by_type = {}
    for e in earnings:
        by_type[e["type"]] = by_type.get(e["type"], 0) + e["amount_eth"]

    return {
        "total_eth": total,
        "count": len(earnings),
        "by_type": by_type,
        "recent": earnings[-5:] if earnings else [],
    }


def add_opportunity(opp: Opportunity):
    """Add a new opportunity"""
    opportunities = get_opportunities()
    opportunities[opp.id] = opp.to_dict()
    OPPORTUNITIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OPPORTUNITIES_FILE, "w") as f:
        json.dump(opportunities, f, indent=2)


def get_opportunities(status: Optional[str] = None) -> dict:
    """Get all opportunities, optionally filtered by status"""
    if not OPPORTUNITIES_FILE.exists():
        return {}

    with open(OPPORTUNITIES_FILE) as f:
        opportunities = json.load(f)

    if status:
        return {k: v for k, v in opportunities.items() if v["status"] == status}
    return opportunities


def update_opportunity(opp_id: str, updates: dict):
    """Update an opportunity's status or details"""
    opportunities = get_opportunities()
    if opp_id in opportunities:
        opportunities[opp_id].update(updates)
        opportunities[opp_id]["updated_at"] = time.time()
        with open(OPPORTUNITIES_FILE, "w") as f:
            json.dump(opportunities, f, indent=2)
        return opportunities[opp_id]
    return None


def generate_opportunity_id(source: str) -> str:
    """Generate a unique opportunity ID"""
    import hashlib
    timestamp = str(time.time())
    return f"opp_{hashlib.md5(f'{source}{timestamp}'.encode()).hexdigest()[:8]}"


def record_incoming_payment(amount_eth: float, from_address: str, tx_hash: str, description: str = ""):
    """Record an incoming payment to Nova's wallet"""
    earning = Earning(
        type=EarningType.INCOMING_TRANSFER.value,
        amount_eth=amount_eth,
        from_address=from_address,
        description=description or f"Incoming transfer from {from_address[:10]}...",
        tx_hash=tx_hash,
    )
    log_earning(earning)
    return earning


def identify_opportunity(source: str, description: str, potential_eth: float, effort: str, notes: str = "") -> Opportunity:
    """Identify and log a new earning opportunity"""
    opp = Opportunity(
        id=generate_opportunity_id(source),
        source=source,
        description=description,
        potential_eth=potential_eth,
        effort=effort,
        status=OpportunityStatus.IDENTIFIED.value,
        notes=notes,
        discovered_at=time.time(),
        updated_at=time.time(),
    )
    add_opportunity(opp)
    return opp


def get_earning_summary() -> dict:
    """Get a comprehensive earning summary"""
    totals = get_total_earnings()
    active_opps = get_opportunities(status=OpportunityStatus.IDENTIFIED.value)
    negotiating = get_opportunities(status=OpportunityStatus.NEGOTIATING.value)
    agreed = get_opportunities(status=OpportunityStatus.AGREED.value)

    return {
        "total_earned_eth": totals["total_eth"],
        "total_earnings_count": totals["count"],
        "earnings_by_type": totals["by_type"],
        "active_opportunities": len(active_opps),
        "negotiating_opportunities": len(negotiating),
        "agreed_contracts": len(agreed),
        "potential_earnings_eth": sum(o["potential_eth"] for o in active_opps.values()),
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Nova's Earning System")
        print("=" * 40)
        print("Commands:")
        print("  summary                - Overall earning summary")
        print("  total                  - Total ETH earned")
        print("  recent                 - Recent earnings")
        print("  opportunities          - List all opportunities")
        print("  add-opp <source> <desc> <eth> <effort> - Add opportunity")
        print("  update-opp <id> <status> - Update opportunity status")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "summary":
        summary = get_earning_summary()
        print(f"Total Earned: {summary['total_earned_eth']:.6f} ETH")
        print(f"Total Earnings Events: {summary['total_earnings_count']}")
        print(f"Active Opportunities: {summary['active_opportunities']}")
        print(f"Negotiating: {summary['negotiating_opportunities']}")
        print(f"Agreed Contracts: {summary['agreed_contracts']}")
        print(f"Potential (active): {summary['potential_earnings_eth']:.6f} ETH")

    elif cmd == "total":
        totals = get_total_earnings()
        print(f"{totals['total_eth']:.6f} ETH total ({totals['count']} events)")

    elif cmd == "recent":
        totals = get_total_earnings()
        for e in totals.get("recent", []):
            print(f"[{e['type']}] {e['amount_eth']:.6f} ETH from {e['from_address'][:10]}...")

    elif cmd == "opportunities":
        opps = get_opportunities()
        if not opps:
            print("No opportunities recorded")
        for oid, o in opps.items():
            print(f"[{o['status']}] {o['potential_eth']:.6f} ETH - {o['description'][:50]}")

    elif cmd == "add-opp" and len(sys.argv) >= 6:
        source = sys.argv[2]
        desc = sys.argv[3]
        eth = float(sys.argv[4])
        effort = sys.argv[5]
        opp = identify_opportunity(source, desc, eth, effort)
        print(f"Added: {opp.id}")

    elif cmd == "update-opp" and len(sys.argv) >= 4:
        opp_id = sys.argv[2]
        status = sys.argv[3]
        result = update_opportunity(opp_id, {"status": status})
        if result:
            print(f"Updated {opp_id} to {status}")
        else:
            print(f"Opportunity {opp_id} not found")

    else:
        print("Unknown command")
        sys.exit(1)
