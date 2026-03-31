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
import { withMarkdownHashHeader } from "@/utils/hash";

const GUARDRAILS_SECTION = `\n\n## AI Guardrails - Code Standards\n\nThis project uses [ai-guardrails](https://github.com/Questi0nM4rk/ai-guardrails) for pedantic code enforcement.\nPre-commit hooks auto-fix formatting, then run security scans, linting, and type checks.\n`;

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

async function writeAgentsMd(
  projectDir: string,
  fileManager: FileManager
): Promise<void> {
  const dest = join(projectDir, "AGENTS.md");
  await fileManager.writeText(dest, withMarkdownHashHeader(buildAgentRules("agents")));
}

async function appendGuardrailsToCLAUDEMd(
  projectDir: string,
  fileManager: FileManager
): Promise<string | null> {
  const claudeMdPath = join(projectDir, "CLAUDE.md");
  const claudeMdExists = await fileManager.exists(claudeMdPath);

  if (claudeMdExists) {
    const existing = await fileManager.readText(claudeMdPath);
    if (existing.includes("## AI Guardrails")) {
      return null;
    }
    await fileManager.appendText(claudeMdPath, GUARDRAILS_SECTION);
    return "CLAUDE.md (appended)";
  }

  await fileManager.writeText(claudeMdPath, `# Project${GUARDRAILS_SECTION}`);
  return "CLAUDE.md (created)";
}

export async function setupAgentInstructionsStep(
  projectDir: string,
  fileManager: FileManager
): Promise<StepResult> {
  try {
    const tools = await detectAgentTools(projectDir, fileManager);
    const knownKeys: Array<keyof DetectedAgentTools> = [
      "claude",
      "cursor",
      "windsurf",
      "copilot",
      "cline",
      "aider",
    ];
    const activeKeys = knownKeys.filter((key) => tools[key]);

    const toolResults = await Promise.all(
      activeKeys.map((key) => writeToolRules(projectDir, fileManager, key))
    );
    const written = toolResults.filter((r): r is string => r !== null);

    // Always generate AGENTS.md regardless of which tools are detected
    await writeAgentsMd(projectDir, fileManager);
    written.push("AGENTS.md");

    // Append guardrails section to CLAUDE.md (create if absent, skip if already present)
    const claudeMdEntry = await appendGuardrailsToCLAUDEMd(projectDir, fileManager);
    if (claudeMdEntry !== null) {
      written.push(claudeMdEntry);
    }

    return ok(`Agent instructions written: ${written.join(", ")}`);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return error(`Agent instructions setup failed: ${message}`);
  }
}
