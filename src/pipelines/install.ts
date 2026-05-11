// Machine-level setup. Verifies the hard dependency (hook-kit on PATH),
// audits which linter prereqs are missing, and — with --upgrade — installs
// them. Does NOT touch any project files. Does NOT mutate the global
// ~/.claude/settings.json. Project-scoped setup belongs in `ai-guardrails init`.
//
// See docs/BUGS.md BUG-001 / BUG-005 for the v4.0 regressions this resolves.

import { ALL_PLUGINS } from "@/languages/registry";
import type { Pipeline, PipelineContext, PipelineResult } from "@/pipelines/types";
import { checkHookKitStep } from "@/steps/check-hook-kit";
import { checkPrerequisites } from "@/steps/check-prerequisites";
import { installPrerequisites } from "@/steps/install-prerequisites";

export const installPipeline: Pipeline = {
  async run(ctx: PipelineContext): Promise<PipelineResult> {
    const hkCheck = await checkHookKitStep(ctx.commandRunner);
    if (hkCheck.status === "error") {
      return { status: "error", message: hkCheck.message };
    }
    ctx.console.info(hkCheck.message);

    const { report } = await checkPrerequisites(
      ctx.console,
      ctx.commandRunner,
      ALL_PLUGINS
    );

    if (ctx.flags.upgrade === true && report.missing.length > 0) {
      const result = await installPrerequisites(
        ctx.console,
        ctx.commandRunner,
        report,
        ctx.projectDir,
        ctx.isTTY,
        ctx.createReadline
      );
      if (result.status === "error") {
        return { status: "error", message: result.message };
      }
    } else if (report.missing.length > 0) {
      ctx.console.info(
        "Run `ai-guardrails install --upgrade` to install missing tools."
      );
    }

    ctx.console.info(
      "Machine setup complete. Run `ai-guardrails init` inside a project to configure it."
    );
    return { status: "ok" };
  },
};
