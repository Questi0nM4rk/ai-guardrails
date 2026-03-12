import { createInterface } from "node:readline";
import { parse as shellParse } from "shell-quote";
import type { CommandRunner } from "@/infra/command-runner";
import type { Console } from "@/infra/console";
import type { StepResult } from "@/models/step-result";
import { ok } from "@/models/step-result";
import type { InstallHint } from "@/runners/types";
import type { PrereqReport } from "@/steps/check-prerequisites";

/** Pick the first available install command from a hint, in preference order. */
function preferredInstallCmd(hint: InstallHint): string | undefined {
  return (
    hint.npm ??
    hint.pip ??
    hint.brew ??
    hint.apt ??
    hint.cargo ??
    hint.go ??
    hint.rustup
  );
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
  projectDir: string
): Promise<void> {
  for (const tool of missing) {
    const cmd = preferredInstallCmd(tool.hint);
    if (!cmd) continue;
    cons.info(`  Installing ${tool.runnerId}...`);
    const parts = shellParse(cmd).filter((t): t is string => typeof t === "string");
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
  interactive = false
): Promise<StepResult> {
  if (report.missing.length === 0) {
    return ok("No missing prerequisites");
  }

  printMissingTools(cons, report.missing);

  const isTTY = process.stdin.isTTY === true || interactive;

  if (!isTTY) {
    cons.warning("\nRun the commands above, then re-run `ai-guardrails init`.");
    return ok("Missing tools listed — install manually and re-run init");
  }

  const rl = createInterface({ input: process.stdin, output: process.stdout });
  let input: string;
  try {
    const answer = await new Promise<string>((resolve) => {
      rl.question("\nInstall missing tools now? [Y/n]: ", resolve);
    });
    input = answer.trim().toLowerCase();
  } finally {
    rl.close();
  }

  if (input === "" || input === "y" || input === "yes") {
    await runInstalls(cons, commandRunner, report.missing, projectDir);
  } else {
    cons.warning("Skipping install. Some checks will be unavailable.");
  }

  return ok("Prerequisite install step complete");
}
