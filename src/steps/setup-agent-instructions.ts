import { dirname, join } from "node:path";
import {
    AGENT_SYMLINKS,
    buildAgentRules,
    type DetectedAgentTools,
    detectAgentTools,
} from "@/generators/agent-rules";
import type { FileManager } from "@/infra/file-manager";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";

async function writeToolRules(
    projectDir: string,
    fileManager: FileManager,
    toolKey: keyof DetectedAgentTools
): Promise<string | null> {
    const symlinkTarget = AGENT_SYMLINKS[toolKey];
    if (!symlinkTarget) return null;

    const dest = join(projectDir, symlinkTarget);
    await fileManager.mkdir(dirname(dest), { parents: true });
    await fileManager.writeText(dest, buildAgentRules(toolKey));
    return symlinkTarget;
}

export async function setupAgentInstructionsStep(
    projectDir: string,
    fileManager: FileManager
): Promise<StepResult> {
    try {
        const tools = await detectAgentTools(projectDir, fileManager);
        const activeKeys = (
            Object.keys(tools) as Array<keyof DetectedAgentTools>
        ).filter((key) => tools[key]);

        const results = await Promise.all(
            activeKeys.map((key) => writeToolRules(projectDir, fileManager, key))
        );
        const written = results.filter((r): r is string => r !== null);

        if (written.length === 0) {
            return ok("No AI agent tool config detected — skipped agent instructions");
        }

        return ok(`Agent instructions written: ${written.join(", ")}`);
    } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return error(`Agent instructions setup failed: ${message}`);
    }
}
