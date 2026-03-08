import { join } from "node:path";
import { z } from "zod";
import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import { classifyFingerprint, loadBaseline } from "@/models/baseline";
import type { LintIssue } from "@/models/lint-issue";
import { BASELINE_PATH } from "@/models/paths";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import { runLinterCollection } from "@/steps/run-linters";

const BaselineEntrySchema = z.object({
    fingerprint: z.string(),
    rule: z.string(),
    linter: z.string(),
    file: z.string(),
    line: z.number(),
    message: z.string(),
    capturedAt: z.string(),
});

export interface StatusStepOutput {
    result: StepResult;
    newIssues: LintIssue[];
    fixedCount: number;
    baselineCount: number;
}

async function loadBaselineFromFile(projectDir: string, fileManager: FileManager) {
    try {
        const text = await fileManager.readText(join(projectDir, BASELINE_PATH));
        const parsed = JSON.parse(text);
        const entries = z.array(BaselineEntrySchema).parse(parsed);
        return loadBaseline(entries);
    } catch {
        return null;
    }
}

export async function statusStep(
    projectDir: string,
    languages: readonly LanguagePlugin[],
    config: ResolvedConfig,
    commandRunner: CommandRunner,
    fileManager: FileManager,
    console: Console
): Promise<StatusStepOutput> {
    try {
        const baseline = await loadBaselineFromFile(projectDir, fileManager);
        const baselineMap = baseline ?? new Map();

        const allIssues = await runLinterCollection(
            projectDir,
            languages,
            config,
            commandRunner,
            fileManager
        );

        const filtered = allIssues.filter(
            (issue) => !config.isAllowed(issue.rule, issue.file)
        );

        const newIssues = filtered.filter(
            (issue) => classifyFingerprint(issue.fingerprint, baselineMap) === "new"
        );

        const currentFingerprints = new Set(filtered.map((i) => i.fingerprint));
        const fixedCount = [...baselineMap.keys()].filter(
            (fp) => !currentFingerprints.has(fp)
        ).length;
        const baselineCount = baselineMap.size;

        const msg = `Status: ${newIssues.length} new, ${fixedCount} fixed, ${baselineCount} baseline`;
        console.info(msg);

        return {
            result: ok(msg),
            newIssues,
            fixedCount,
            baselineCount,
        };
    } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return {
            result: error(`Status check failed: ${message}`),
            newIssues: [],
            fixedCount: 0,
            baselineCount: 0,
        };
    }
}
