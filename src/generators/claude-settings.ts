import { ALL_RULE_GROUPS, collectDenyGlobs } from "@/check/rules/groups";
import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import { HOOK_COMMAND } from "@/hooks/command";

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
  // Deny globs always include every group regardless of disabled_groups —
  // settings.json deny patterns are a static safety net independent of the
  // hook-level config toggle.
  const settings: ClaudeSettings = {
    permissions: {
      deny: collectDenyGlobs(ALL_RULE_GROUPS),
    },
    hooks: {
      PreToolUse: [
        { matcher: "Bash", hooks: [{ type: "command", command: HOOK_COMMAND }] },
        {
          matcher: "Edit|Write|NotebookEdit",
          hooks: [{ type: "command", command: HOOK_COMMAND }],
        },
        { matcher: "Read", hooks: [{ type: "command", command: HOOK_COMMAND }] },
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
