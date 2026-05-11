// Verify the ai-guardrails-hk-cc-tools binary is on PATH. Generated CC hooks
// reference it by unqualified name, so we surface mismatches at init time
// rather than letting hooks silently no-op (BUG-008).
//
// Soft warning, not hard error: tests and dev environments often run init
// from a source tree where dist/ isn't on PATH. The warning is enough to
// catch the real-world case (user installs v3 via curl, runs init from a
// local v4 dev tree — hooks would point at v4 binaries the runtime can't
// resolve).

import type { CommandRunner } from "@/infra/command-runner";
import type { Console } from "@/infra/console";
import type { StepResult } from "@/models/step-result";
import { ok } from "@/models/step-result";

const INSTALL_HINT =
  "Install: curl -fsSL https://raw.githubusercontent.com/Questi0nM4rk/ai-guardrails/main/scripts/install.sh | sh";

export async function checkHkBinariesStep(
  commandRunner: CommandRunner,
  cons: Console
): Promise<StepResult> {
  const ccResult = await commandRunner.run(["ai-guardrails-hk-cc-tools", "--version"]);
  if (ccResult.exitCode !== 0) {
    cons.warning(
      `ai-guardrails-hk-cc-tools not found on PATH — generated hooks will ` +
        `reference it by name and silently fail to launch.\n  ${INSTALL_HINT}`
    );
    return ok("ai-guardrails-hk-cc-tools missing — warning emitted");
  }
  return ok("ai-guardrails-hk-cc-tools on PATH");
}
