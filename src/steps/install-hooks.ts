import { homedir } from "node:os";
import { join } from "node:path";
import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import {
  type ClaudeSettings,
  ClaudeSettingsSchema,
  mergeHooks,
} from "@/utils/merge-claude-settings";

// 60s matches CC's default hook timeout and stays under the 120s default
// Bash tool budget. See SPEC-014.
const HOOK_TIMEOUT = 60;
const BINARY = "ai-guardrails-hk-cc-tools";

const GUARDRAILS_HOOKS = [
  {
    matcher: "Bash|Edit|Write|NotebookEdit|Read",
    hooks: [{ type: "command", command: BINARY, timeout: HOOK_TIMEOUT }],
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
      try {
        const parsed: unknown = JSON.parse(content);
        const result = ClaudeSettingsSchema.safeParse(parsed);
        if (result.success) {
          existing = result.data;
        }
      } catch {
        cons.warning(
          "~/.claude/settings.json contains invalid JSON — merging from scratch"
        );
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
