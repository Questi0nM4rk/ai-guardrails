import { dirname, join } from "node:path";
import type { ConfigStrategy, ResolvedConfig } from "@/config/schema";
import { generateLefthookConfig, lefthookGenerator } from "@/generators/lefthook";
import { ALL_GENERATORS, applicableGenerators } from "@/generators/registry";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import { applyStrategy } from "@/utils/config-merge";
import { HASH_PREFIX, JSONC_HASH_PREFIX, MD_HASH_PREFIX } from "@/utils/hash";

async function runGenerator(
  projectDir: string,
  fileManager: FileManager,
  id: string,
  configFile: string,
  generate: () => string,
  strategy: ConfigStrategy
): Promise<{ file: string; skipped?: true } | { error: string }> {
  try {
    // Check skip condition BEFORE calling generate() so that a throwing
    // generator (e.g. lefthook without active plugins) does not mask a skip.
    const dest = join(projectDir, configFile);
    const exists = await fileManager.exists(dest);
    if (exists && strategy === "skip") {
      return { file: configFile, skipped: true };
    }

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
  const activeIds = new Set(languages.map((l) => l.id));
  const applicable = applicableGenerators(activeIds);

  const results = await Promise.all(
    applicable.map((g) => {
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

  const removed: string[] = [];
  if (strategy === "replace") {
    const inactive = ALL_GENERATORS.filter(
      (g) => g.languages !== undefined && !g.languages.some((id) => activeIds.has(id))
    );
    for (const g of inactive) {
      try {
        const dest = join(projectDir, g.configFile);
        if (await fileManager.exists(dest)) {
          const content = await fileManager.readText(dest);
          const firstLine = content.split("\n")[0] ?? "";
          if (
            firstLine.startsWith(HASH_PREFIX) ||
            firstLine.startsWith(JSONC_HASH_PREFIX) ||
            firstLine.startsWith(MD_HASH_PREFIX)
          ) {
            await fileManager.delete(dest);
            removed.push(g.configFile);
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        errors.push(`${g.id} cleanup: ${msg}`);
      }
    }
  }

  const parts: string[] = [];
  if (written.length > 0) {
    parts.push(`Generated ${written.length} config file(s): ${written.join(", ")}`);
  }
  if (skipped.length > 0) {
    parts.push(`Skipped ${skipped.length} existing file(s): ${skipped.join(", ")}`);
  }
  if (removed.length > 0) {
    parts.push(`Removed ${removed.length} stale config(s): ${removed.join(", ")}`);
  }

  if (errors.length > 0) {
    return error(`Config generation failed: ${errors.join(", ")}`);
  }

  return ok(parts.length > 0 ? parts.join("; ") : "No config files generated");
}
