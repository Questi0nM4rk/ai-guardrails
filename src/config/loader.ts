import { join } from "node:path";
import { parse as parseToml } from "smol-toml";
import {
  buildResolvedConfig,
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
  } catch {
    return {};
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

export function resolveConfig(machine: MachineConfig, project: ProjectConfig): ResolvedConfig {
  return buildResolvedConfig(machine, project);
}
