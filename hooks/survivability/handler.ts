import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

const handler = async (event: any) => {
  // Only run on gateway startup
  if (event.type !== "gateway" || event.action !== "startup") {
    return;
  }

  console.log("[nova-preflight] Running startup health check...");

  try {
    const workspaceDir = event.context?.cfg?.workspace?.dir || "/home/sntrblck/.openclaw/workspace";
    
    const checks = {
      workspace: await checkWorkspace(workspaceDir),
      memory: await checkMemory(workspaceDir),
      breakers: await checkBreakers(workspaceDir),
      skills: await checkSkills(workspaceDir)
    };

    // Write health snapshot
    const healthFile = `${workspaceDir}/memory/health_summary.md`;
    const summary = generateHealthSummary(checks);
    
    await writeFile(healthFile, summary);

    console.log("[nova-preflight] Health check complete. Status:", JSON.stringify(checks));

  } catch (err) {
    console.error("[nova-preflight] Preflight failed:", err);
  }
};

async function checkWorkspace(dir: string): Promise<object> {
  try {
    const { stdout } = await execAsync(`ls -la ${dir}/SOUL.md ${dir}/AGENTS.md ${dir}/memory/ 2>&1`);
    return { ok: true, path: dir };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

async function checkMemory(dir: string): Promise<object> {
  try {
    const { stdout } = await execAsync(`ls ${dir}/memory/*.json ${dir}/memory/*.md 2>/dev/null | wc -l`);
    const count = parseInt(stdout.trim()) || 0;
    return { ok: count > 0, files: count };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

async function checkBreakers(dir: string): Promise<object> {
  try {
    const { stdout } = await execAsync(`ls ${dir}/memory/breakers/*.json 2>/dev/null | wc -l`);
    const count = parseInt(stdout.trim()) || 0;
    return { ok: true, breakers: count };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

async function checkSkills(dir: string): Promise<object> {
  try {
    const { stdout } = await execAsync(`ls ${dir}/skills/advanced_memory/*.py 2>/dev/null | wc -l`);
    const count = parseInt(stdout.trim()) || 0;
    return { ok: count >= 5, skills: count };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

function generateHealthSummary(checks: any): string {
  const timestamp = new Date().toISOString();
  const allOk = Object.values(checks).every((c: any) => c.ok);
  
  return `# Health Summary

Generated: ${timestamp}

## Status: ${allOk ? "✅ NOMINAL" : "⚠️ DEGRADED"}

### Checks
${Object.entries(checks).map(([name, result]: [string, any]) => 
  `- **${name}**: ${result.ok ? "✅" : "❌"} ${JSON.stringify(result)}`
).join("\n")}

## Recent Incidents
\`\`\`
$(tail -5 ${process.cwd()}/memory/incidents.log 2>/dev/null || echo "No recent incidents")
\`\`\`
`;
}

async function writeFile(path: string, content: string): Promise<void> {
  const fs = await import("fs/promises");
  await fs.writeFile(path, content, "utf-8");
}

export default handler;