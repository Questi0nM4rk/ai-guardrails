import type { CommandRunner } from "@/infra/command-runner";
import type { Console } from "@/infra/console";
import type { InstallHint } from "@/runners/types";
import { ok } from "@/models/step-result";
import type { StepResult } from "@/models/step-result";
import type { PrereqReport } from "@/steps/check-prerequisites";

/** Pick the first available install command from a hint, in preference order. */
function preferredInstallCmd(hint: InstallHint): string | undefined {
  return hint.npm ?? hint.pip ?? hint.brew ?? hint.apt ?? hint.cargo ?? hint.go ?? hint.rustup;
}

function printMissingTools(cons: Console, missing: PrereqReport["missing"]): void {
  cons.warning(`\nMissing tools (${missing.length}):`);
  for (const tool of missing) {
    cons.warning(`  ${tool.runnerId} — ${tool.hint.description}`);
    const cmd = preferredInstallCmd(tool.hint);
    if (cmd) {
      cons.warning(`    Install: ${cmd}`);
    }
  }
}

async function runInstalls(
  cons: Console,
  commandRunner: CommandRunner,
  missing: PrereqReport["missing"],
  projectDir: string,
): Promise<void> {
  for (const tool of missing) {
    const cmd = preferredInstallCmd(tool.hint);
    if (!cmd) continue;
    cons.info(`  Installing ${tool.runnerId}...`);
    const parts = cmd.split(" ");
    const result = await commandRunner.run(parts, { cwd: projectDir });
    if (result.exitCode === 0) {
      cons.info(`  ${tool.runnerId} installed`);
    } else {
      cons.warning(`  Failed to install ${tool.runnerId}. Run manually: ${cmd}`);
    }
  }
}

export async function installPrerequisites(
  cons: Console,
  commandRunner: CommandRunner,
  report: PrereqReport,
  projectDir: string,
): Promise<StepResult> {
  if (report.missing.length === 0) {
    return ok("No missing prerequisites");
  }

  printMissingTools(cons, report.missing);

  const isTTY = process.stdin.isTTY === true;

  if (!isTTY) {
    cons.warning("\nRun the commands above, then re-run `ai-guardrails init`.");
    return ok("Missing tools listed — install manually and re-run init");
  }

  process.stdout.write("\nInstall missing tools now? [Y/n]: ");

  for await (const line of console) {
    const input = line.trim().toLowerCase();
    if (input === "" || input === "y" || input === "yes") {
      await runInstalls(cons, commandRunner, report.missing, projectDir);
    } else {
      cons.warning("Skipping install. Some checks will be unavailable.");
    }
    break;
  }

  return ok("Prerequisite install step complete");
}
