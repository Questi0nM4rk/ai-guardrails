import { homedir } from "node:os";
import { join } from "node:path";
import { loadMachineConfig, loadProjectConfig, resolveConfig } from "@/config/loader";
import type { ResolvedConfig } from "@/config/schema";
import type { FileManager } from "@/infra/file-manager";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";

export async function loadConfigStep(
    projectDir: string,
    fileManager: FileManager
): Promise<{ result: StepResult; config: ResolvedConfig | null }> {
    try {
        const machinePath = join(homedir(), ".ai-guardrails", "config.toml");
        const machine = await loadMachineConfig(machinePath, fileManager);
        const project = await loadProjectConfig(projectDir, fileManager);
        const config = resolveConfig(machine, project);
        return {
            result: ok(`Config loaded: profile=${config.profile}`),
            config,
        };
    } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return {
            result: error(`Config load failed: ${message}`),
            config: null,
        };
    }
}
