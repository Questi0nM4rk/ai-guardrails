import { homedir } from "node:os";
import { join } from "node:path";
import { z } from "zod";
import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import { type ClaudeSettings, mergeHooks } from "@/utils/merge-claude-settings";

/** Lenient schema — accepts any valid JSON object as ClaudeSettings */
const ClaudeSettingsSchema: z.ZodType<ClaudeSettings> = z.object({}).passthrough();

const GUARDRAILS_HOOKS = [
  {
    matcher: "Bash",
    hooks: [
      {
        type: "command",
        command:
          "command -v ai-guardrails >/dev/null 2>&1 || exit 0; ai-guardrails hook dangerous-cmd",
      },
    ],
  },
  {
    matcher: "Edit|Write|NotebookEdit",
    hooks: [
      {
        type: "command",
        command:
          "command -v ai-guardrails >/dev/null 2>&1 || exit 0; ai-guardrails hook protect-configs",
      },
    ],
  },
  {
    matcher: "Read",
    hooks: [
      {
        type: "command",
        command:
          "command -v ai-guardrails >/dev/null 2>&1 || exit 0; ai-guardrails hook protect-reads",
      },
    ],
  },
] as const;

export async function installHooksStep(
  fileManager: FileManager,
  cons: Console,
  claudeDir?: string
): Promise<StepResult> {
  try {
    const dir = claudeDir ?? join(homedir(), ".claude");
    const settingsPath = join(dir, "settings.json");
    let existing: ClaudeSettings = {};

    if (await fileManager.exists(settingsPath)) {
      const content = await fileManager.readText(settingsPath);
      const parsed: unknown = JSON.parse(content);
      const result = ClaudeSettingsSchema.safeParse(parsed);
      if (result.success) {
        existing = result.data;
      }
    }

    const merged = mergeHooks(existing, GUARDRAILS_HOOKS);

    await fileManager.mkdir(dir, { parents: true });
    await fileManager.writeText(settingsPath, JSON.stringify(merged, null, 2));

    cons.info("Merged hooks into ~/.claude/settings.json");
    return ok("Hooks merged into ~/.claude/settings.json");
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return error(`Failed to merge hooks: ${message}`);
  }
}
