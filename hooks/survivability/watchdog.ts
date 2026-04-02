import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

const handler = async (event: any) => {
  // Only run on command:stop or session:compact:after
  if (event.type !== "command" && !(event.type === "session" && event.action === "compact:after")) {
    return;
  }

  console.log("[nova-watchdog] Processing:", event.type, event.action);

  try {
    const workspaceDir = event.context?.cfg?.workspace?.dir || "/home/sntrblck/.openclaw/workspace";
    
    // Run lightweight health probe
    await runHealthProbe(workspaceDir);
    
    // Check for deadletter items and alert if significant
    await checkDeadletter(workspaceDir);
    
    console.log("[nova-watchdog] Watchdog check complete");
  } catch (err) {
    console.error("[nova-watchdog] Failed:", err);
  }
};

async function runHealthProbe(workspaceDir: string): Promise<void> {
  try {
    // Run breakers status check
    const { stdout } = await execAsync(
      `cd ${workspaceDir}/skills/advanced_memory && python3 breakers.py status 2>&1`,
      { timeout: 5000 }
    );
    
    // Check if any breakers are open
    if (stdout.includes("open")) {
      console.log("[nova-watchdog] ⚠️ Circuit breaker(s) open detected");
    }
  } catch (err) {
    // Non-critical, just log
    console.log("[nova-watchdog] Health probe skipped or failed:", String(err).slice(0, 100));
  }
}

async function checkDeadletter(workspaceDir: string): Promise<void> {
  try {
    const { stdout } = await execAsync(
      `cd ${workspaceDir}/skills/advanced_memory && python3 deadletter.py stats 2>&1`,
      { timeout: 5000 }
    );
    
    // Parse stats
    const stats = JSON.parse(stdout);
    if (stats.pending > 3) {
      console.log(`[nova-watchdog] ⚠️ ${stats.pending} pending deadletter items`);
    }
  } catch (err) {
    // Non-critical
  }
}

export default handler;