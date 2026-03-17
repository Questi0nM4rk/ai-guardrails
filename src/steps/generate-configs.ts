import { dirname, join } from "node:path";
import type { ConfigStrategy, ResolvedConfig } from "@/config/schema";
import { generateLefthookConfig, lefthookGenerator } from "@/generators/lefthook";
import { ALL_GENERATORS } from "@/generators/registry";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import { applyStrategy } from "@/utils/config-merge";

async function runGenerator(
  projectDir: string,
  fileManager: FileManager,
  id: string,
  configFile: string,
  generate: () => string,
  strategy: ConfigStrategy
): Promise<{ file: string; skipped?: true } | { error: string }> {
  try {
    const generated = generate();
    const content = await applyStrategy(
      projectDir,
      configFile,
      generated,
      strategy,
      fileManager
    );

    if (content === null) {
      return { file: configFile, skipped: true };
    }

    const dest = join(projectDir, configFile);
    await fileManager.mkdir(dirname(dest), { parents: true });
    await fileManager.writeText(dest, content);
    return { file: configFile };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { error: `${id}: ${message}` };
  }
}

export async function generateConfigsStep(
  projectDir: string,
  languages: readonly LanguagePlugin[],
  config: ResolvedConfig,
  fileManager: FileManager,
  strategy: ConfigStrategy = "merge"
): Promise<StepResult> {
  const results = await Promise.all(
    ALL_GENERATORS.map((g) => {
      const generate =
        g.id === lefthookGenerator.id
          ? () => generateLefthookConfig(config, languages)
          : () => g.generate(config);
      return runGenerator(
        projectDir,
        fileManager,
        g.id,
        g.configFile,
        generate,
        strategy
      );
    })
  );

  const written: string[] = [];
  const skipped: string[] = [];
  const errors: string[] = [];
  for (const r of results) {
    if ("error" in r) {
      errors.push(r.error);
    } else if (r.skipped === true) {
      skipped.push(r.file);
    } else {
      written.push(r.file);
    }
  }

  if (errors.length > 0) {
    return error(`Config generation failed: ${errors.join(", ")}`);
  }

  const parts: string[] = [];
  if (written.length > 0) {
    parts.push(`Generated ${written.length} config file(s): ${written.join(", ")}`);
  }
  if (skipped.length > 0) {
    parts.push(`Skipped ${skipped.length} existing file(s): ${skipped.join(", ")}`);
  }

  return ok(parts.join("; "));
}
