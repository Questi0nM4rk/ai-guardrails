import { join } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { generateLefthookConfig } from "@/generators/lefthook";
import type { CommandRunner } from "@/infra/command-runner";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";

export async function setupHooksStep(
  projectDir: string,
  languages: readonly LanguagePlugin[],
  config: ResolvedConfig,
  fileManager: FileManager,
  commandRunner: CommandRunner
): Promise<StepResult> {
  try {
    const content = generateLefthookConfig(config, languages);
    const dest = join(projectDir, "lefthook.yml");
    await fileManager.writeText(dest, content);

    const result = await commandRunner.run(["lefthook", "install"], {
      cwd: projectDir,
    });

    if (result.exitCode !== 0) {
      return error(
        `lefthook install failed (exit ${result.exitCode}): ${result.stderr.trim()}`
      );
    }

    return ok("Hooks installed via lefthook");
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return error(`Hook setup failed: ${message}`);
  }
}
