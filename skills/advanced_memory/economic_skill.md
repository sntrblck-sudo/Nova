# Economic Action Skill

Use this skill when Nova needs to take economic action or check wallet status.

## Quick Reference

```bash
cd /home/sntrblck/.openclaw/workspace/cdp-nova

# Check balance
python3 economic_system.py status

# Send ETH (tier-based)
python3 economic_system.py send <address> <amount_eth>

# Check what tier an action would be
python3 economic_system.py tier <address> <amount_eth>

# View recent actions
python3 economic_system.py recent
```

## Tier System

| Tier | Trigger | Action |
|------|---------|--------|
| 1 - AUTOMATIC | ≤0.001 ETH to approved recipient | Executes immediately |
| 2 - SURFACE | >0.001 ETH or new recipient ≤0.0001 ETH | Surfaces to Sen for approval |
| 3 - ASK | >0.001 ETH or new recipient >0.0001 ETH | Must ask Sen explicitly |

## Approved Recipients
- `0x1b7eDF6F5FCAb52b680661cC82306E3DaCA7943C` — Sen
- `0xB743fdbA842379933A3774617786712458659D16` — Nova Primary
- `0x21f2155Cba0B599D705B4cf6e51Ba157503bcD0B` — Nova Backup

## Reserve Policy
- Minimum balance: 0.0002 ETH (for gas)
- Automatic txs blocked if they'd drop below reserve

## Surfacing Pending Actions
When an action surfaces (Tier 2):
1. Log it with status "pending_approval"
2. Tell Sen: amount, recipient, and that it needs approval
3. Wait for confirmation before executing
4. If denied, do not execute

## Escalation Format
When surfacing to Sen:
```
💰 Economic Action — Approval Needed

Amount: X.XXXXXX ETH
To: 0x...... (recipient address)
Tier: 2 (SURFACE)
Reserve after: X.XXXXXX ETH

Reply "approve" to execute or "deny" to cancel.
```
