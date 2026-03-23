import { homedir } from "node:os";
import { join } from "node:path";
import { loadMachineConfig, loadProjectConfig, resolveConfig } from "@/config/loader";
import { ALL_INIT_MODULES } from "@/init/registry";
import { executeModules } from "@/init/runner";
import { applyFlagDisables } from "@/init/selections";
import type { InitContext } from "@/init/types";
import { runWizard } from "@/init/wizard";
import { PROJECT_CONFIG_PATH } from "@/models/paths";
import type { Pipeline, PipelineContext, PipelineResult } from "@/pipelines/types";
import { detectLanguagesStep } from "@/steps/detect-languages";

async function configExists(
  projectDir: string,
  ctx: PipelineContext
): Promise<boolean> {
  try {
    await ctx.fileManager.readText(join(projectDir, PROJECT_CONFIG_PATH));
    return true;
  } catch {
    return false;
  }
}

async function buildInitContext(
  ctx: PipelineContext,
  selections: Map<string, boolean>
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

export const initPipeline: Pipeline = {
  async run(ctx: PipelineContext): Promise<PipelineResult> {
    const force = ctx.flags.force === true;
    const upgrade = ctx.flags.upgrade === true;
    const yes = ctx.flags.yes === true;
    const isInteractive = (ctx.isTTY || ctx.flags.interactive === true) && !yes;

    const exists = await configExists(ctx.projectDir, ctx);
    if (exists && !force && !upgrade) {
      return {
        status: "error",
        message:
          ".ai-guardrails/config.toml already exists. Use --force to overwrite or --upgrade to refresh.",
      };
    }

    if (isInteractive) {
      ctx.console.info("Running interactive init...");
    } else {
      ctx.console.info("Running non-interactive init with defaults...");
    }

    // Build InitContext once for language detection and config loading.
    const preliminary = await buildInitContext(ctx, new Map());
    if (preliminary.initCtx === null) {
      return {
        status: "error",
        message: preliminary.error ?? "Language detection failed",
      };
    }

    let selections: Map<string, boolean>;
    if (isInteractive) {
      selections = await runWizard(preliminary.initCtx, ALL_INIT_MODULES);
    } else {
      // Apply --no-X flag disables on top of module defaults
      selections = applyFlagDisables(ALL_INIT_MODULES, ctx.flags);
    }

    // Reuse the already-built context — just swap in the final selections.
    const initCtx = { ...preliminary.initCtx, selections };

    const results = await executeModules(ALL_INIT_MODULES, initCtx);
    const errorMessages = results
      .filter((r) => r.status === "error")
      .map((r) => r.message);

    return errorMessages.length > 0
      ? { status: "error", message: `Init failed: ${errorMessages.join("; ")}` }
      : { status: "ok" };
  },
};
