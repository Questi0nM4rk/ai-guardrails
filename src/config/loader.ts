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

async function readTomlSafe(
  path: string,
  fm: FileManager
): Promise<Record<string, unknown>> {
  let text: string;
  try {
    text = await fm.readText(path);
  } catch {
    return {}; // file not found — expected when no config exists
  }
  if (!text.trim()) return {};
  // Let parse errors propagate so callers surface malformed config to the user
  const parsed: Record<string, unknown> = parseToml(text);
  return parsed;
}

export async function loadMachineConfig(
  path: string,
  fm: FileManager
): Promise<MachineConfig> {
  const raw = await readTomlSafe(path, fm);
  return MachineConfigSchema.parse(raw);
}

export async function loadProjectConfig(
  projectDir: string,
  fm: FileManager
): Promise<ProjectConfig> {
  const path = join(projectDir, ".ai-guardrails", "config.toml");
  const raw = await readTomlSafe(path, fm);
  return ProjectConfigSchema.parse(raw);
}

export function resolveConfig(
  machine: MachineConfig,
  project: ProjectConfig
): ResolvedConfig {
  return buildResolvedConfig(machine, project);
}
