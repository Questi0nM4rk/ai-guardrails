// Verify hook-kit is on PATH; install fails loud rather than emitting a
// fail-open hook command that silently exits 0 on the first triggered rule.

import type { CommandRunner } from "@/infra/command-runner";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";

const INSTALL_HINT =
  "Install with: npm i -g @questi0nm4rk/hook-kit  (or: bun i -g @questi0nm4rk/hook-kit)";

export async function checkHookKitStep(
  commandRunner: CommandRunner
): Promise<StepResult> {
  const result = await commandRunner.run(["hook-kit", "--version"]);
  if (result.exitCode === 0) {
    const version = result.stdout.trim() || "unknown";
    return ok(`hook-kit ${version} on PATH`);
  }
  return error(
    `hook-kit binary not found on PATH — ai-guardrails depends on it for ` +
      `escalation routing.\n  ${INSTALL_HINT}`
  );
}
