import { join } from "node:path";
import type { FileManager } from "@/infra/file-manager";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";

const CI_WORKFLOW = `name: AI Guardrails Check
on:
  push:
    branches: ["**"]
  pull_request:
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2
      - run: bunx ai-guardrails check
`;

export async function setupCiStep(
  projectDir: string,
  fileManager: FileManager
): Promise<StepResult> {
  try {
    const workflowDir = join(projectDir, ".github", "workflows");
    await fileManager.mkdir(workflowDir, { parents: true });

    const dest = join(workflowDir, "ai-guardrails.yml");
    await fileManager.writeText(dest, CI_WORKFLOW);

    return ok("CI workflow written to .github/workflows/ai-guardrails.yml");
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return error(`CI setup failed: ${message}`);
  }
}
