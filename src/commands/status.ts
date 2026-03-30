import { buildContext } from "@/commands/context";
import type { Console } from "@/infra/console";
import { detectLanguagesStep } from "@/steps/detect-languages";
import { loadConfigStep } from "@/steps/load-config";
import { statusStep } from "@/steps/status-step";
import { getVersion, semverLt } from "@/utils/version";

/**
 * Print version status to console and optionally write a warning to stderr.
 * Extracted for unit testability — pure side-effects, no process.exit.
 *
 * Returns the stderr warning string if one was emitted, or undefined.
 */
export function printVersionStatus(
  installed: string,
  minVersion: string | undefined,
  cons: Console
): string | undefined {
  if (minVersion !== undefined && semverLt(installed, minVersion)) {
    const warning = `Version mismatch: project requires >=${minVersion}, installed ${installed}`;
    cons.warning(warning);
    cons.info(`Version: ${installed} (pinned: >=${minVersion})`);
    return warning;
  }
  if (minVersion !== undefined) {
    cons.info(`Version: ${installed} (pinned: >=${minVersion})`);
    return undefined;
  }
  cons.info(`Version: ${installed} (not pinned — run init to pin)`);
  return undefined;
}

export async function runStatus(
  projectDir: string,
  flags: Record<string, unknown>
): Promise<void> {
  const ctx = buildContext(projectDir, flags);
  const { fileManager, commandRunner, console: cons } = ctx;

  cons.step("Detecting languages...");
  const { result: detectResult, languages } = await detectLanguagesStep(
    projectDir,
    fileManager
  );
  if (detectResult.status === "error") {
    process.stderr.write(`Error: ${detectResult.message}\n`);
    process.exit(2);
  }
  cons.success(detectResult.message);

  cons.step("Loading config...");
  const { result: configResult, config } = await loadConfigStep(
    projectDir,
    fileManager
  );
  if (configResult.status === "error" || config === null) {
    process.stderr.write(`Error: ${configResult.message ?? "config load failed"}\n`);
    process.exit(2);
  }
  cons.success(configResult.message);

  printVersionStatus(getVersion(), config.minVersion, cons);

  await statusStep(projectDir, languages, config, commandRunner, fileManager, cons);
  // status never exits 1 — informational only
}
