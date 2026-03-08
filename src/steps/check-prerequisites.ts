import type { CommandRunner } from "@/infra/command-runner";
import type { Console } from "@/infra/console";
import type { LanguagePlugin } from "@/languages/types";
import type { StepResult } from "@/models/step-result";
import { ok } from "@/models/step-result";
import type { InstallHint, LinterRunner } from "@/runners/types";

export interface MissingTool {
    runnerId: string;
    hint: InstallHint;
}

export interface PrereqReport {
    missing: MissingTool[];
    available: string[];
}

/** Collect all unique runners across plugins, keyed by id. */
function uniqueRunners(plugins: readonly LanguagePlugin[]): LinterRunner[] {
    const seen = new Set<string>();
    const runners: LinterRunner[] = [];
    for (const plugin of plugins) {
        for (const runner of plugin.runners()) {
            if (!seen.has(runner.id)) {
                seen.add(runner.id);
                runners.push(runner);
            }
        }
    }
    return runners;
}

export async function checkPrerequisites(
    cons: Console,
    commandRunner: CommandRunner,
    plugins: readonly LanguagePlugin[]
): Promise<{ result: StepResult; report: PrereqReport }> {
    const runners = uniqueRunners(plugins);

    const results = await Promise.all(
        runners.map(async (runner) => ({
            runner,
            isAvail: await runner.isAvailable(commandRunner),
        }))
    );

    const missing: MissingTool[] = [];
    const available: string[] = [];

    for (const { runner, isAvail } of results) {
        if (isAvail) {
            available.push(runner.id);
        } else {
            missing.push({ runnerId: runner.id, hint: runner.installHint });
        }
    }

    const report: PrereqReport = { missing, available };

    if (missing.length === 0) {
        cons.success(`All ${available.length} prerequisite tool(s) available`);
    } else {
        cons.warning(
            `${available.length} tool(s) available, ${missing.length} missing`
        );
    }

    return { result: ok("Prerequisite check complete"), report };
}
