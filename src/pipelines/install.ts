import { ConfigStrategySchema } from "@/config/schema";
import type { Pipeline, PipelineContext, PipelineResult } from "@/pipelines/types";
import { getBiomeVersion } from "@/runners/biome";
import { detectLanguagesStep } from "@/steps/detect-languages";
import { generateConfigsStep } from "@/steps/generate-configs";
import { loadConfigStep } from "@/steps/load-config";
import { setupAgentInstructionsStep } from "@/steps/setup-agent-instructions";
import { setupCiStep } from "@/steps/setup-ci";
import { setupHooksStep } from "@/steps/setup-hooks";
import { validateConfigsStep } from "@/steps/validate-configs";
import { detectNoConsoleLevel } from "@/utils/detect-project-type";

export const installPipeline: Pipeline = {
  async run(ctx: PipelineContext): Promise<PipelineResult> {
    const { projectDir, fileManager, commandRunner, console: cons } = ctx;

    cons.step("Detecting languages...");
    const { result: detectResult, languages } = await detectLanguagesStep(
      projectDir,
      fileManager
    );
    if (detectResult.status === "error") {
      return { status: "error", message: detectResult.message };
    }
    cons.success(detectResult.message);

    cons.step("Loading config...");
    const { result: configResult, config } = await loadConfigStep(
      projectDir,
      fileManager
    );
    if (configResult.status === "error" || config === null) {
      return { status: "error", message: configResult.message };
    }
    cons.success(configResult.message);

    // Detect noConsole level and biome version only when TypeScript is active
    // (biome is the only consumer of both)
    const hasTypeScript = languages.some((l) => l.id === "typescript");
    let noConsoleLevel = config.noConsoleLevel;
    let biomeVersion: string | undefined;
    if (hasTypeScript) {
      const pkgJsonPath = `${projectDir}/package.json`;
      const pkgJsonExists = await fileManager.exists(pkgJsonPath);
      if (pkgJsonExists) {
        const pkgJsonText = await fileManager.readText(pkgJsonPath);
        let parsed: unknown;
        try {
          parsed = JSON.parse(pkgJsonText);
        } catch {
          parsed = null;
        }
        noConsoleLevel = detectNoConsoleLevel(parsed);
      }
      biomeVersion = await getBiomeVersion(commandRunner, projectDir);
    }
    const configWithConsoleLevel = {
      ...config,
      noConsoleLevel,
      values: {
        ...config.values,
        ...(biomeVersion !== undefined && { biome_version: biomeVersion }),
      },
    };

    cons.step("Generating configs...");
    const rawStrategy = ctx.flags.configStrategy;
    const strategyParsed = ConfigStrategySchema.safeParse(rawStrategy ?? "merge");
    if (!strategyParsed.success) {
      return {
        status: "error",
        message: `Invalid --config-strategy value "${String(rawStrategy)}". Must be one of: merge, replace, skip.`,
      };
    }
    const configStrategy = strategyParsed.data;
    const genResult = await generateConfigsStep(
      projectDir,
      languages,
      configWithConsoleLevel,
      fileManager,
      configStrategy
    );
    if (genResult.status === "error") {
      return { status: "error", message: genResult.message };
    }
    cons.success(genResult.message);

    cons.step("Validating configs...");
    const activeLanguageIds = new Set(languages.map((l) => l.id));
    const validateResult = await validateConfigsStep(
      projectDir,
      fileManager,
      activeLanguageIds
    );
    if (validateResult.status === "error") {
      return { status: "error", message: validateResult.message };
    }
    cons.success(validateResult.message);

    const noHooks = ctx.flags.noHooks === true;
    if (!noHooks) {
      cons.step("Installing hooks...");
      const hooksResult = await setupHooksStep(
        projectDir,
        languages,
        configWithConsoleLevel,
        fileManager,
        commandRunner
      );
      if (hooksResult.status === "error") {
        cons.warning(`Hook setup failed: ${hooksResult.message}`);
      } else {
        cons.success(hooksResult.message);
      }
    }

    const noCi = ctx.flags.noCi === true;
    if (!noCi) {
      cons.step("Setting up CI...");
      const ciResult = await setupCiStep(projectDir, fileManager);
      if (ciResult.status === "error") {
        cons.warning(`CI setup failed: ${ciResult.message}`);
      } else {
        cons.success(ciResult.message);
      }
    }

    const noAgentRules = ctx.flags.noAgentRules === true;
    if (!noAgentRules) {
      cons.step("Setting up agent instructions...");
      const agentResult = await setupAgentInstructionsStep(projectDir, fileManager);
      if (agentResult.status === "error") {
        cons.warning(`Agent instructions failed: ${agentResult.message}`);
      } else {
        cons.success(agentResult.message);
      }
    }

    return { status: "ok" };
  },
};
