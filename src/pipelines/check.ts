import type { Pipeline, PipelineContext, PipelineResult } from "@/pipelines/types";
import { checkStep } from "@/steps/check-step";
import { detectLanguagesStep } from "@/steps/detect-languages";
import { loadConfigStep } from "@/steps/load-config";
import type { ReportFormat } from "@/steps/report-step";
import { reportStep } from "@/steps/report-step";

export const checkPipeline: Pipeline = {
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

        cons.step("Running checks...");
        const { result: checkResult, issues } = await checkStep(
            projectDir,
            languages,
            config,
            commandRunner,
            fileManager,
            cons
        );

        const format = (ctx.flags.format as ReportFormat | undefined) ?? "text";
        await reportStep(issues, format, cons, fileManager);

        if (checkResult.status === "error") {
            return {
                status: "error",
                message: checkResult.message,
                issueCount: issues.length,
            };
        }

        cons.success(checkResult.message);
        return { status: "ok", issueCount: issues.length };
    },
};
