import { homedir } from "node:os";
import { join } from "node:path";
import { loadMachineConfig, loadProjectConfig, resolveConfig } from "@/config/loader";
import { ALL_INIT_MODULES } from "@/init/registry";
import { executeModules } from "@/init/runner";
import { applyFlagDisables } from "@/init/selections";
import type { InitContext } from "@/init/types";
import type { Pipeline, PipelineContext, PipelineResult } from "@/pipelines/types";
import { detectLanguagesStep } from "@/steps/detect-languages";

async function buildInstallContext(ctx: PipelineContext): Promise<InitContext> {
  const { languages } = await detectLanguagesStep(ctx.projectDir, ctx.fileManager);

  const machinePath = join(homedir(), ".ai-guardrails", "config.toml");
  const machine = await loadMachineConfig(machinePath, ctx.fileManager);
  const project = await loadProjectConfig(ctx.projectDir, ctx.fileManager);
  const config = resolveConfig(machine, project);

  const selections = applyFlagDisables(ALL_INIT_MODULES, ctx.flags);

  return {
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
}

export const installPipeline: Pipeline = {
  async run(ctx: PipelineContext): Promise<PipelineResult> {
    const initCtx = await buildInstallContext(ctx);
    const results = await executeModules(ALL_INIT_MODULES, initCtx);
    const hasError = results.some((r) => r.status === "error");

    return hasError
      ? { status: "error", message: "One or more install modules failed" }
      : { status: "ok" };
  },
};
