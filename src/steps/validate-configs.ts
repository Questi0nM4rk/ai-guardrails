import type { FileManager } from "@/infra/file-manager";
import { ALL_GENERATORS } from "@/generators/registry";
import { error, ok } from "@/models/step-result";
import type { StepResult } from "@/models/step-result";
import { join } from "node:path";

async function validateOne(
  dest: string,
  configFile: string,
  fileManager: FileManager,
): Promise<string | null> {
  try {
    const content = await fileManager.readText(dest);
    if (!content.trim()) return `empty: ${configFile}`;
    return null;
  } catch {
    return `missing: ${configFile}`;
  }
}

export async function validateConfigsStep(
  projectDir: string,
  fileManager: FileManager,
): Promise<StepResult> {
  const problems = (
    await Promise.all(
      ALL_GENERATORS.map((g) =>
        validateOne(join(projectDir, g.configFile), g.configFile, fileManager),
      ),
    )
  ).filter((p): p is string => p !== null);

  if (problems.length > 0) {
    return error(`Config validation failed: ${problems.join(", ")}`);
  }

  return ok(`All ${ALL_GENERATORS.length} config files validated`);
}
