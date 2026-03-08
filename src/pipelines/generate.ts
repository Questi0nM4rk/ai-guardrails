import type { Pipeline, PipelineContext, PipelineResult } from "@/pipelines/types";
import { detectLanguagesStep } from "@/steps/detect-languages";
import { loadConfigStep } from "@/steps/load-config";
import { generateConfigsStep } from "@/steps/generate-configs";
import { validateConfigsStep } from "@/steps/validate-configs";

export const generatePipeline: Pipeline = {
  async run(ctx: PipelineContext): Promise<PipelineResult> {
    const { projectDir, fileManager, console: cons } = ctx;

    cons.step("Detecting languages...");
    const { result: detectResult } = await detectLanguagesStep(projectDir, fileManager);
    if (detectResult.status === "error") {
      return { status: "error", message: detectResult.message };
    }
    cons.success(detectResult.message);

    cons.step("Loading config...");
    const { result: configResult, config } = await loadConfigStep(projectDir, fileManager);
    if (configResult.status === "error" || config === null) {
      return { status: "error", message: configResult.message };
    }
    cons.success(configResult.message);

    cons.step("Generating configs...");
    const genResult = await generateConfigsStep(projectDir, config, fileManager);
    if (genResult.status === "error") {
      return { status: "error", message: genResult.message };
    }
    cons.success(genResult.message);

    const checkMode = ctx.flags.check === true;
    if (checkMode) {
      cons.step("Validating configs...");
      const validateResult = await validateConfigsStep(projectDir, fileManager);
      if (validateResult.status === "error") {
        return { status: "error", message: validateResult.message };
      }
      cons.success(validateResult.message);
    }

    return { status: "ok" };
  },
};
