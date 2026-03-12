import { dirname, join } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { generateLefthookConfig, lefthookGenerator } from "@/generators/lefthook";
import { ALL_GENERATORS } from "@/generators/registry";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";

async function runGenerator(
  projectDir: string,
  fileManager: FileManager,
  id: string,
  configFile: string,
  generate: () => string
): Promise<{ file: string } | { error: string }> {
  try {
    const content = generate();
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
  fileManager: FileManager
): Promise<StepResult> {
  const results = await Promise.all(
    ALL_GENERATORS.map((g) => {
      const generate =
        g.id === lefthookGenerator.id
          ? () => generateLefthookConfig(config, languages)
          : () => g.generate(config);
      return runGenerator(projectDir, fileManager, g.id, g.configFile, generate);
    })
  );

  const written: string[] = [];
  const errors: string[] = [];
  for (const r of results) {
    if ("file" in r) written.push(r.file);
    else errors.push(r.error);
  }

  if (errors.length > 0) {
    return error(`Config generation failed: ${errors.join(", ")}`);
  }

  return ok(`Generated ${written.length} config file(s): ${written.join(", ")}`);
}
