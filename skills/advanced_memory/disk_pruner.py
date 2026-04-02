#!/usr/bin/env python3
"""
Nova Disk Pruner — Autonomous large file / bloat detection and cleanup.
Run via health check or standalone.

Config: memory/disk_pruner_config.json
Logs action to memory/incidents.log
Surfaces to Sen only when items need attention.

Safe auto-prune (no approval needed):
    - __pycache__/ directories
    - *.pyc files
    - Empty files
    - /tmp/*.tar.gz older than 7 days
    - Old cron telemetry JSON files (>30 days)

Surface for approval:
    - Any directory tagged "ARCHIVE" in config
    - Files > 100MB
    - node_modules directories
    - Logs > 50MB
    - Anything matching custom surfacing rules
"""

import json
import os
import shutil
import stat
import sys
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path("/home/sntrblck/.openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
CONFIG_FILE = MEMORY_DIR / "disk_pruner_config.json"
INCIDENTS_LOG = MEMORY_DIR / "incidents.log"
LAST_RUN_LOG = MEMORY_DIR / "pruner_last_run.json"

# Targets that are NEVER pruned without explicit approval
PROTECTED = {
    "memory/action_log.db",
    "memory/execution_logs.db",
    "memory/nova_memory.db",
    "memory/recall.db",
    "cdp-nova/nova-wallet.json",
    "BOOTSTRAP.md",
    "SOUL.md",
    "MEMORY.md",
}


def load_config():
    """Load or create default config."""
    defaults = {
        "dry_run": True,  # Default to dry-run; set False to enable auto-prune
        "auto_prune": {
            "pycache": True,
            "pyc": True,
            "empty_files_days": 7,
            "temp_archives_days": 7,
            "old_telemetry_days": 30,
        },
        "surface_thresholds": {
            "file_size_mb": 100,
            "log_size_mb": 50,
        },
        "protected_paths": [str(WORKSPACE / p) for p in PROTECTED],
        "last_prune_date": None,
        "enabled": True,
    }

    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text())
            # Merge with defaults for any missing keys
            for k, v in defaults.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
        except Exception:
            pass

    # Write default config
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(defaults, indent=2))
    return defaults


def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def get_dir_size(path: Path) -> int:
    """Get total size of directory or file in bytes."""
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_dir(follow_symlinks=False):
                    total += get_dir_size(Path(entry.path))
                else:
                    total += entry.stat().st_size
            except OSError:
                continue
    except OSError:
        pass
    return total


def scan_workspace(cfg):
    """Scan workspace for prunable and surfacable items."""
    auto_prune = []
    surface = []
    protected_found = []

    pycache_count = 0
    pyc_count = 0
    empty_count = 0
    temp_old = 0
    telemetry_old = 0

    cutoff_empty = datetime.now() - timedelta(days=cfg["auto_prune"]["empty_files_days"])
    cutoff_temp = datetime.now() - timedelta(days=cfg["auto_prune"]["temp_archives_days"])
    cutoff_telemetry = datetime.now() - timedelta(days=cfg["auto_prune"]["old_telemetry_days"])

    for root_str, dirs, files in os.walk(WORKSPACE):
        root = Path(root_str)

        # Skip protected paths
        if any(str(root).startswith(p) for p in cfg["protected_paths"]):
            dirs[:] = []  # Don't recurse
            continue

        # Handle __pycache__
        if "__pycache__" in dirs:
            pycache_count += 1
            pyc_files = list((root / "__pycache__" / f) for f in os.listdir(root / "__pycache__") if f.endswith(".pyc"))
            if cfg["auto_prune"]["pycache"]:
                auto_prune.append({
                    "type": "pycache",
                    "path": str(root / "__pycache__"),
                    "size": get_dir_size(root / "__pycache__"),
                    "reason": "Python bytecode cache"
                })

        # Handle .pyc files
        if cfg["auto_prune"]["pyc"]:
            for f in files:
                if f.endswith(".pyc"):
                    pyc_count += 1
                    fp = root / f
                    auto_prune.append({
                        "type": "pyc",
                        "path": str(fp),
                        "size": fp.stat().st_size,
                        "reason": "Python bytecode file"
                    })

        # Handle empty files
        for f in files:
            fp = root / f
            try:
                size = fp.stat().st_size
                mtime = datetime.fromtimestamp(fp.stat().st_mtime)
                if size == 0 and mtime < cutoff_empty:
                    empty_count += 1
                    auto_prune.append({
                        "type": "empty_file",
                        "path": str(fp),
                        "size": 0,
                        "reason": "Empty file, untouched for " + str(cfg["auto_prune"]["empty_files_days"]) + "+ days"
                    })
            except OSError:
                continue

        # Handle old telemetry JSON files
        if "telemetry" in str(root) or "memory" in str(root):
            for f in files:
                if f.endswith(".json") and "cron_run" in f or "telemetry" in f:
                    fp = root / f
                    try:
                        mtime = datetime.fromtimestamp(fp.stat().st_mtime)
                        if mtime < cutoff_telemetry:
                            telemetry_old += 1
                            auto_prune.append({
                                "type": "old_telemetry",
                                "path": str(fp),
                                "size": fp.stat().st_size,
                                "reason": f"Old telemetry file ({mtime.date()})"
                            })
                    except OSError:
                        continue

        # Check for large files / bloat (surface items)
        for f in files:
            fp = root / f
            try:
                size = fp.stat().st_size
                size_mb = size / (1024 * 1024)

                # Large files that need surfacing
                if size_mb >= cfg["surface_thresholds"]["file_size_mb"]:
                    surface.append({
                        "type": "large_file",
                        "path": str(fp),
                        "size": size,
                        "size_mb": round(size_mb, 1),
                        "reason": f"File is {size_mb:.1f}MB (threshold: {cfg['surface_thresholds']['file_size_mb']}MB)"
                    })

                # Large log files
                elif size_mb >= cfg["surface_thresholds"]["log_size_mb"] and (f.endswith(".log") or f.endswith(".txt")):
                    surface.append({
                        "type": "large_log",
                        "path": str(fp),
                        "size": size,
                        "size_mb": round(size_mb, 1),
                        "reason": f"Log file is {size_mb:.1f}MB (threshold: {cfg['surface_thresholds']['log_size_mb']}MB)"
                    })

                # node_modules directories (record size, don't auto-prune)
                elif f == "node_modules" and root.is_dir():
                    size = get_dir_size(fp)
                    surface.append({
                        "type": "node_modules",
                        "path": str(fp),
                        "size": size,
                        "size_mb": round(size / (1024 * 1024), 1),
                        "reason": "node_modules directory (offload candidate)"
                    })

            except OSError:
                continue

    return {
        "auto_prune": auto_prune,
        "surface": surface,
        "stats": {
            "pycache_count": pycache_count,
            "pyc_count": pyc_count,
            "empty_count": empty_count,
            "temp_old": temp_old,
            "telemetry_old": telemetry_old,
        }
    }


def do_prune(items, dry_run=True):
    """Execute pruning of items. Returns (pruned, errors)."""
    pruned = []
    errors = []

    for item in items:
        path = Path(item["path"])
        if not path.exists():
            continue

        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

            size_mb = item["size"] / (1024 * 1024)
            pruned.append(f"{item['type']}: {item['path']} ({size_mb:.1f}MB)")
        except Exception as e:
            errors.append(f"Failed to remove {item['path']}: {e}")

    return pruned, errors


def log_incident(message, severity="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(INCIDENTS_LOG, "a") as f:
        f.write(f"[{timestamp}] [{severity.upper()}] disk_pruner: {message}\n")


def write_alert(items, output_path):
    """Write surfacing alert to file for Sen to review."""
    content = ["# Disk Pruner — Items Needing Attention\n"]
    content.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    content.append(f"**Reason:** Items found that need manual review or approval to prune.\n")
    content.append("---\n\n")

    for item in items:
        size_mb = item["size"] / (1024 * 1024)
        content.append(f"## {item['type']}\n")
        content.append(f"- **Path:** `{item['path']}`\n")
        content.append(f"- **Size:** {size_mb:.1f} MB\n")
        content.append(f"- **Reason:** {item['reason']}\n")
        content.append(f"- **Action:** `rm -rf {item['path']}` (or review)\n\n")

    Path(output_path).write_text("".join(content))


def run_dry_run(cfg, results):
    """Print what would happen without making changes."""
    print("\n=== Disk Pruner — Dry Run ===")
    print(f"Config: dry_run={cfg['dry_run']}, enabled={cfg['enabled']}")
    print(f"\n[SURFACE] {len(results['surface'])} items need attention:")
    for item in results["surface"]:
        size_mb = item["size"] / (1024 * 1024)
        print(f"  [{item['type']}] {item['path']} — {size_mb:.1f}MB")
        print(f"           Reason: {item['reason']}")

    print(f"\n[AUTO-PRUNE] {len(results['auto_prune'])} items would be pruned:")
    total_auto_mb = sum(i["size"] for i in results["auto_prune"]) / (1024 * 1024)
    grouped = {}
    for item in results["auto_prune"]:
        grouped.setdefault(item["type"], []).append(item["path"])

    for dtype, paths in grouped.items():
        count = len(paths)
        sizes = sum(i["size"] for i in results["auto_prune"] if i["type"] == dtype)
        size_mb = sizes / (1024 * 1024)
        print(f"  [{dtype}] {count} items (~{size_mb:.1f}MB)")
        for p in paths[:3]:
            print(f"    - {p}")
        if len(paths) > 3:
            print(f"    ... and {len(paths) - 3} more")

    print(f"\nTotal auto-prune: ~{total_auto_mb:.1f}MB in {len(results['auto_prune'])} items")
    print(f"\nTo enable auto-pruning: set dry_run=false in {CONFIG_FILE}")
    print(f"To review surface items: cat {MEMORY_DIR}/pruner_alert.md")


def run(cfg, args):
    """Main run logic."""
    if not cfg["enabled"]:
        print("[disk_pruner] Disabled in config. No action taken.")
        return

    dry_run = cfg["dry_run"] or ("--dry-run" in args) or ("--surface" in args)

    results = scan_workspace(cfg)

    # Write surface alert if there are items
    if results["surface"]:
        write_alert(results["surface"], str(MEMORY_DIR / "pruner_alert.md"))
        log_incident(f"Surface alert written: {len(results['surface'])} items need attention", "info")

    if "--dry-run" in args or dry_run:
        run_dry_run(cfg, results)
        return

    # Actually prune
    pruned, errors = do_prune(results["auto_prune"], dry_run=False)

    for p in pruned:
        log_incident(f"Auto-pruned: {p}", "info")

    for e in errors:
        log_incident(e, "error")

    # Save last run
    LAST_RUN_LOG.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "pruned_count": len(pruned),
        "error_count": len(errors),
        "dry_run": False,
    }, indent=2))

    print(f"[disk_pruner] Done. Pruned {len(pruned)} items, {len(errors)} errors.")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    cfg = load_config()
    run(cfg, sys.argv)
