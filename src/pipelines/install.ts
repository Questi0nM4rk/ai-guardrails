import { homedir } from "node:os";
import { join } from "node:path";
import { loadMachineConfig, loadProjectConfig, resolveConfig } from "@/config/loader";
import { ALL_INIT_MODULES } from "@/init/registry";
import { executeModules } from "@/init/runner";
import { applyFlagDisables } from "@/init/selections";
import type { InitContext } from "@/init/types";
import type { Pipeline, PipelineContext, PipelineResult } from "@/pipelines/types";
import { detectLanguagesStep } from "@/steps/detect-languages";
import { installHooksStep } from "@/steps/install-hooks";

async function buildInstallContext(
  ctx: PipelineContext
): Promise<{ initCtx: InitContext | null; error?: string }> {
  const { result: detectResult, languages } = await detectLanguagesStep(
    ctx.projectDir,
    ctx.fileManager
  );
  if (detectResult.status === "error") {
    return { initCtx: null, error: detectResult.message };
  }

  const machinePath = join(homedir(), ".ai-guardrails", "config.toml");
  const machine = await loadMachineConfig(machinePath, ctx.fileManager);
  const project = await loadProjectConfig(ctx.projectDir, ctx.fileManager);
  const config = resolveConfig(machine, project);

  const selections = applyFlagDisables(ALL_INIT_MODULES, ctx.flags);

  const initCtx: InitContext = {
    projectDir: ctx.projectDir,
    fileManager: ctx.fileManager,
    commandRunner: ctx.commandRunner,
    console: ctx.console,
    config,
    languages,
    selections,
    isTTY: ctx.isTTY,
    createReadline: ctx.createReadline,
    flags: ctx.flags,
  };

  return { initCtx };
}

export const installPipeline: Pipeline = {
  async run(ctx: PipelineContext): Promise<PipelineResult> {
    const { initCtx, error } = await buildInstallContext(ctx);
    if (initCtx === null) {
      return { status: "error", message: error ?? "Language detection failed" };
    }

    const results = await executeModules(ALL_INIT_MODULES, initCtx);
    const errorMessages = results
      .filter((r) => r.status === "error")
      .map((r) => r.message);

    if (errorMessages.length > 0) {
      return {
        status: "error",
        message: `Install failed: ${errorMessages.join("; ")}`,
      };
    }

    const hooksResult = await installHooksStep(ctx.fileManager, ctx.console);
    if (hooksResult.status === "error") {
      return { status: "error", message: hooksResult.message };
    }

    return { status: "ok" };
  },
};
