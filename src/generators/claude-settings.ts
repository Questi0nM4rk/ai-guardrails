import { ALL_RULE_GROUPS, collectDenyGlobs } from "@/check/rules/groups";
import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";

interface HookEntry {
  type: string;
  command: string;
}

interface PreToolUseEntry {
  matcher: string;
  hooks: HookEntry[];
}

interface ClaudeSettings {
  permissions: {
    deny: readonly string[];
  };
  hooks: {
    PreToolUse: PreToolUseEntry[];
  };
}

function renderClaudeSettings(_config: ResolvedConfig): string {
  // settings.json must be strict JSON (no comments) for all JSON parsers.
  // Staleness/tamper detection is handled by validate-configs comparing
  // regenerated content against on-disk content directly.
  //
  // Always emit ALL deny globs regardless of disabled_groups config.
  // settings.json deny patterns are a first-layer static safety net,
  // independent of hook-level config toggling.
  const guard = "[ ! -f ./dist/ai-guardrails ] && exit 0";
  const settings: ClaudeSettings = {
    permissions: {
      deny: collectDenyGlobs(ALL_RULE_GROUPS),
    },
    hooks: {
      PreToolUse: [
        {
          matcher: "Bash",
          hooks: [
            {
              type: "command",
              command: `${guard}; ./dist/ai-guardrails hook dangerous-cmd`,
            },
          ],
        },
        {
          matcher: "Edit|Write|NotebookEdit",
          hooks: [
            {
              type: "command",
              command: `${guard}; ./dist/ai-guardrails hook protect-configs`,
            },
          ],
        },
        {
          matcher: "Read",
          hooks: [
            {
              type: "command",
              command: `${guard}; ./dist/ai-guardrails hook protect-reads`,
            },
          ],
        },
      ],
    },
  };
  return JSON.stringify(settings, null, 2);
}

export const claudeSettingsGenerator: ConfigGenerator = {
  id: "claude-settings",
  configFile: ".claude/settings.json",
  generate(config: ResolvedConfig): string {
    return renderClaudeSettings(config);
  },
};
