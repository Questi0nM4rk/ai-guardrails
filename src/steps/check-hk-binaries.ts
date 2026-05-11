// Verify the two ai-guardrails-hk binaries are on PATH. Generated CC hooks
// reference them by unqualified name, so init refuses to write hooks pointing
// at binaries the runtime can't actually resolve (BUG-008).

import type { CommandRunner } from "@/infra/command-runner";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";

const INSTALL_HINT =
  "Install: curl -fsSL https://raw.githubusercontent.com/Questi0nM4rk/ai-guardrails/main/scripts/install.sh | sh";

export async function checkHkBinariesStep(
  commandRunner: CommandRunner
): Promise<StepResult> {
  const ccResult = await commandRunner.run(["ai-guardrails-hk-cc-tools", "--version"]);
  if (ccResult.exitCode !== 0) {
    return error(
      `ai-guardrails-hk-cc-tools binary not found on PATH — generated hooks ` +
        `would reference a non-existent binary.\n  ${INSTALL_HINT}`
    );
  }

  return ok(`ai-guardrails-hk-cc-tools on PATH`);
}
