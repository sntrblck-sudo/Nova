#!/bin/bash
# Nova's daily staking report
# Run daily at 9 AM ET via OpenClaw cron

cd /home/sntrblck/.openclaw/workspace/cdp-nova

# Check positions
python3 staking.py status >> /tmp/nova_staking_daily.log 2>&1

# Get CLAWS pending
python3 compound.py check >> /tmp/nova_staking_daily.log 2>&1

# If meaningful rewards, claim and log
python3 compound.py >> /tmp/nova_staking_daily.log 2>&1

# Append to persistent log
cat /tmp/nova_staking_daily.log >> /home/sntrblck/.openclaw/workspace/memory/compound_log.jsonl 2>/dev/null

# Clean temp
rm -f /tmp/nova_staking_daily.log
