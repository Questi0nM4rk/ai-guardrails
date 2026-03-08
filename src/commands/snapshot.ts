import { buildContext } from "@/commands/context";
import { detectLanguagesStep } from "@/steps/detect-languages";
import { loadConfigStep } from "@/steps/load-config";
import { snapshotStep } from "@/steps/snapshot-step";

export async function runSnapshot(
    projectDir: string,
    flags: Record<string, unknown>
): Promise<void> {
    const ctx = buildContext(projectDir, flags);
    const { fileManager, commandRunner, console: cons } = ctx;

    cons.step("Detecting languages...");
    const { result: detectResult, languages } = await detectLanguagesStep(
        projectDir,
        fileManager
    );
    if (detectResult.status === "error") {
        process.stderr.write(`Error: ${detectResult.message}\n`);
        process.exit(2);
    }
    cons.success(detectResult.message);

    cons.step("Loading config...");
    const { result: configResult, config } = await loadConfigStep(
        projectDir,
        fileManager
    );
    if (configResult.status === "error" || config === null) {
        process.stderr.write(
            `Error: ${configResult.message ?? "config load failed"}\n`
        );
        process.exit(2);
    }
    cons.success(configResult.message);

    cons.step("Capturing snapshot...");
    const baselinePath =
        typeof flags.baseline === "string" ? flags.baseline : undefined;
    const result = await snapshotStep(
        projectDir,
        languages,
        config,
        commandRunner,
        fileManager,
        baselinePath
    );
    if (result.status === "error") {
        process.stderr.write(`Error: ${result.message}\n`);
        process.exit(2);
    }
    cons.success(result.message);
}
