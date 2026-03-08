import { join } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";

/**
 * Resolve a CLI tool to its executable path.
 *
 * Checks `<projectDir>/node_modules/.bin/<toolName>` first so compiled
 * binaries (which don't inherit node_modules/.bin in PATH) can still invoke
 * locally-installed tools.  Falls back to the bare tool name (global PATH
 * lookup) when the local binary is absent.  Returns null when neither works.
 */
export async function resolveToolPath(
    toolName: string,
    projectDir: string,
    commandRunner: CommandRunner
): Promise<string | null> {
    const localPath = join(projectDir, "node_modules", ".bin", toolName);
    const localResult = await commandRunner.run([localPath, "--version"], {
        cwd: projectDir,
    });
    if (localResult.exitCode === 0) return localPath;
    const globalResult = await commandRunner.run([toolName, "--version"]);
    if (globalResult.exitCode === 0) return toolName;
    return null;
}
