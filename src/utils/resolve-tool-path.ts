import { join } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";

// Cache keyed by "toolName:projectDir" — stores the Promise so concurrent
// callers awaiting the same key don't each spawn their own --version probes.
const resolveCache = new Map<string, Promise<string | null>>();

async function performResolve(
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

/**
 * Resolve a CLI tool to its executable path.
 *
 * Checks `<projectDir>/node_modules/.bin/<toolName>` first so compiled
 * binaries (which don't inherit node_modules/.bin in PATH) can still invoke
 * locally-installed tools.  Falls back to the bare tool name (global PATH
 * lookup) when the local binary is absent.  Returns null when neither works.
 *
 * Results are cached per (toolName, projectDir) pair so repeated calls
 * (e.g. isAvailable() followed by run()) do not re-spawn --version probes.
 */
export async function resolveToolPath(
  toolName: string,
  projectDir: string,
  commandRunner: CommandRunner
): Promise<string | null> {
  const key = `${toolName}:${projectDir}`;
  let pending = resolveCache.get(key);
  if (pending === undefined) {
    pending = performResolve(toolName, projectDir, commandRunner);
    resolveCache.set(key, pending);
  }
  return pending;
}

/** Clear the resolve cache — intended for test isolation only. */
export function clearResolveToolPathCache(): void {
  resolveCache.clear();
}
