import type { ResolvedConfig } from "@/config/schema";
import type { FileManager } from "@/infra/file-manager";
import { ALL_GENERATORS } from "@/generators/registry";
import { error, ok } from "@/models/step-result";
import type { StepResult } from "@/models/step-result";
import { dirname, join } from "node:path";

async function runGenerator(
  projectDir: string,
  config: ResolvedConfig,
  fileManager: FileManager,
  generator: (typeof ALL_GENERATORS)[number],
): Promise<{ file: string } | { error: string }> {
  try {
    const content = generator.generate(config);
    const dest = join(projectDir, generator.configFile);
    await fileManager.mkdir(dirname(dest), { parents: true });
    await fileManager.writeText(dest, content);
    return { file: generator.configFile };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { error: `${generator.id}: ${message}` };
  }
}

export async function generateConfigsStep(
  projectDir: string,
  config: ResolvedConfig,
  fileManager: FileManager,
): Promise<StepResult> {
  const results = await Promise.all(
    ALL_GENERATORS.map((g) => runGenerator(projectDir, config, fileManager, g)),
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
