# Research: VPS Sub-Agent Deployment Guidebook
**Source:** Copilot-generated guide for OpenClaw agents managing sub-agents on VPS
**Saved:** 2026-04-01
**File:** memory/research/vps-subagent-guidebook.pdf

## Summary
A comprehensive technical guidebook on how an OpenClaw main agent can autonomously provision, deploy, manage, and decommission sub-agents on VPS infrastructure.

## Key Sections

### 1. OpenClaw Architecture
- Main Agent = coordinator (orchestrates, delegates, maintains context)
- Sub-Agents = isolated workers for parallelizable tasks
- Lifecycle: Provisioning → Deployment → Operation → Monitoring → Updating → Decommissioning

### 2. VPS Provider Comparison
| Provider | Specs | Monthly Cost |
|----------|-------|-------------|
| Hetzner | 4GB RAM / 2vCPU / 40GB NVMe | €4.35 |
| Vultr | 1GB RAM / 1vCPU / 25GB SSD | $5.00 |
| DigitalOcean | 1GB RAM / 1vCPU / 25GB SSD | $6.00 |
| AWS EC2 t3.micro | 1GB RAM / 2vCPU / 8GB SSD | ~$8.50 |

**Note:** Hetzner offers best price/performance for EU-based deployments.

### 3. Automated Provisioning
- **CLI tools:** doctl (DigitalOcean), hetznerctl (Hetzner), etc.
- **IaC:** Terraform for declarative, repeatable provisioning
- **Cloud-Init:** User-data scripts for post-provisioning setup

### 4. Security Baseline
- SSH key-only authentication (no passwords)
- UFW/firewall restricting ports
- Automatic security updates (unattended-upgrades)
- CIS Benchmarks hardening
- Secrets management for API keys

### 5. Communication & Observability
- Main ↔ Sub-agent secure communication
- Health monitoring
- Centralized logging

## How This Relates to Nova's Current Setup

### Already Doing (via OpenClaw built-in)
- ✅ Main agent orchestration
- ✅ Sub-agent spawning (sessions_spawn)
- ✅ Health checks and monitoring (nova-health-check cron)
- ✅ Isolated session management

### Not Yet Explored
- ❌ Direct VPS provisioning (Nova doesn't have her own cloud infrastructure)
- ❌ Terraform/IaC for declarative infra
- ❌ Docker containerization of sub-agents
- ❌ Cross-VPS sub-agent communication

## Potential Nova Applications
1. **Nova deploys specialist sub-agents on cheap VPS** (e.g., Hetzner) for specific tasks
2. **Nova manages her own VPS infrastructure** autonomously
3. **Agent swarm orchestration** — Nova as coordinator of multiple VPS-hosted workers

## Risks / Considerations
- Nova would need cloud API credentials (AWS, Hetzner, DO, etc.)
- Billing responsibility — autonomous spending on cloud resources
- Security surface increases significantly with VPS-level access
- Complexity of managing fleet of sub-agents across machines

## Next Steps
- Determine if Nova should have cloud provider credentials
- Evaluate Hetzner for cost-effective sub-agent hosting
- Consider Dockerization approach for portable sub-agents
- Explore OpenClaw's existing containerization support
