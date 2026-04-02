#!/usr/bin/env python3
"""
Nova Action Logger - Python CLI
Query the unified action audit trail

Usage:
    python3 action_logger.py summary [days]
    python3 action_logger.py actions [--type TYPE] [--category CAT] [--outcome OUTCOME] [--limit N]
    python3 action_logger.py decisions [--type TYPE] [--limit N]
    python3 action_logger.py pending
"""

import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

LOG_DB = Path("/home/sntrblck/.openclaw/workspace/memory/action_log.db")


def get_db():
    if not LOG_DB.exists():
        print("Error: action_log.db not found.")
        exit(1)
    return sqlite3.connect(LOG_DB)


def query_actions(action_type=None, category=None, outcome=None, limit=100):
    conn = get_db()
    cur = conn.cursor()
    sql = "SELECT id, timestamp, action_type, category, description, rationale, outcome, outcome_detail FROM actions WHERE 1=1"
    params = []
    if action_type:
        sql += " AND action_type = ?"
        params.append(action_type)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if outcome:
        sql += " AND outcome = ?"
        params.append(outcome)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    cur.execute(sql, params)
    return cur.fetchall()


def query_decisions(decision_type=None, limit=50):
    conn = get_db()
    cur = conn.cursor()
    sql = "SELECT id, timestamp, decision_type, context, choice, rationale, confidence FROM decisions WHERE 1=1"
    params = []
    if decision_type:
        sql += " AND decision_type = ?"
        params.append(decision_type)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    return cur.fetchall()


def get_summary(days=7):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM actions WHERE timestamp >= ?", (since,))
    total = cur.fetchone()[0]
    cur.execute("SELECT outcome, COUNT(*) FROM actions WHERE timestamp >= ? GROUP BY outcome", (since,))
    by_outcome = dict(cur.fetchall())
    cur.execute("SELECT category, COUNT(*) FROM actions WHERE timestamp >= ? GROUP BY category ORDER BY COUNT(*) DESC", (since,))
    by_category = dict(cur.fetchall())
    cur.execute("SELECT COUNT(*) FROM decisions WHERE timestamp >= ?", (since,))
    decisions = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM actions WHERE outcome = 'pending'")
    pending = cur.fetchone()[0]
    return {'period_days': days, 'total_actions': total, 'by_outcome': by_outcome, 'by_category': by_category, 'total_decisions': decisions, 'pending': pending}


def print_summary(days=7):
    s = get_summary(days)
    print(f"\n=== Nova Action Log Summary (last {days} days) ===")
    print(f"Total actions: {s['total_actions']}")
    print(f"Total decisions: {s['total_decisions']}")
    print(f"Pending outcomes: {s['pending']}")
    if s['by_outcome']:
        print("\nBy outcome:")
        for k, v in s['by_outcome'].items():
            print(f"  {k}: {v}")
    if s['by_category']:
        print("\nBy category:")
        for k, v in s['by_category'].items():
            print(f"  {k}: {v}")


def print_actions(rows):
    if not rows:
        print("No actions found.")
        return
    print(f"{'ID':<6} {'Timestamp':<28} {'Type':<15} {'Cat':<10} {'Outcome':<10} Description")
    print("-" * 100)
    for r in rows:
        desc = r[4][:55] + "..." if len(r[4]) > 55 else r[4]
        print(f"{r[0]:<6} {r[1]:<28} {r[2]:<15} {r[3]:<10} {r[6]:<10} {desc}")


def print_decisions(rows):
    if not rows:
        print("No decisions found.")
        return
    print(f"{'ID':<6} {'Timestamp':<28} {'Type':<15} Choice")
    print("-" * 90)
    for r in rows:
        choice = r[4][:40] + "..." if len(r[4]) > 40 else r[4]
        print(f"{r[0]:<6} {r[1]:<28} {r[2]:<15} {choice}")


def main():
    parser = argparse.ArgumentParser(description="Nova Action Logger")
    sub = parser.add_subparsers(dest='cmd')
    
    p_summary = sub.add_parser('summary', help='Show summary')
    p_summary.add_argument('days', nargs='?', type=int, default=7)
    
    p_actions = sub.add_parser('actions', help='Query actions')
    p_actions.add_argument('--type')
    p_actions.add_argument('--category')
    p_actions.add_argument('--outcome')
    p_actions.add_argument('--limit', type=int, default=50)
    
    p_decisions = sub.add_parser('decisions', help='Query decisions')
    p_decisions.add_argument('--type')
    p_decisions.add_argument('--limit', type=int, default=50)
    
    sub.add_parser('pending', help='Show pending actions')
    
    args = parser.parse_args()
    
    if args.cmd == 'summary' or args.cmd is None:
        print_summary(getattr(args, 'days', 7))
    elif args.cmd == 'actions':
        print_actions(query_actions(action_type=args.type, category=args.category, outcome=args.outcome, limit=args.limit))
    elif args.cmd == 'decisions':
        print_decisions(query_decisions(decision_type=args.type, limit=args.limit))
    elif args.cmd == 'pending':
        print_actions(query_actions(outcome='pending'))


if __name__ == '__main__':
    main()
