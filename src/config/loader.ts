import { join } from "node:path";
import { parse as parseToml } from "smol-toml";
import {
  type MachineConfig,
  MachineConfigSchema,
  type ProjectConfig,
  ProjectConfigSchema,
  type ResolvedConfig,
} from "@/config/schema";
import type { FileManager } from "@/infra/file-manager";

export type { MachineConfig, ProjectConfig, ResolvedConfig };

async function readTomlSafe(path: string, fm: FileManager): Promise<Record<string, unknown>> {
  try {
    const text = await fm.readText(path);
    if (!text.trim()) return {};
    return parseToml(text) as Record<string, unknown>;
  } catch (err: unknown) {
    if (err instanceof Error && "code" in err && (err as NodeJS.ErrnoException).code === "ENOENT") {
      return {};
    }
    throw err;
  }
}

export async function loadMachineConfig(path: string, fm: FileManager): Promise<MachineConfig> {
  const raw = await readTomlSafe(path, fm);
  return MachineConfigSchema.parse(raw);
}

export async function loadProjectConfig(
  projectDir: string,
  fm: FileManager,
): Promise<ProjectConfig> {
  const path = join(projectDir, ".ai-guardrails", "config.toml");
  const raw = await readTomlSafe(path, fm);
  return ProjectConfigSchema.parse(raw);
}

export { buildResolvedConfig as resolveConfig } from "@/config/schema";
