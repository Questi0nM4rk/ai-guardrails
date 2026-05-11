import { ALL_RULE_GROUPS, collectDenyGlobs } from "@/check/rules/groups";
import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";

interface HookEntry {
  type: "command";
  command: string;
  timeout: number;
}

interface MatcherEntry {
  matcher: string;
  hooks: HookEntry[];
}

interface ClaudeSettings {
  permissions: { deny: readonly string[] };
  hooks: { PreToolUse: MatcherEntry[]; PostToolUse: MatcherEntry[] };
}

// 60s matches CC's default hook timeout and stays under the 120s default
// Bash tool budget. Hooks that block longer than the agent's tool timeout
// orphan when the agent abandons the call. See SPEC-014.
const HOOK_TIMEOUT_SECONDS = 60;
const BINARY_NAME = "ai-guardrails-hk-cc-tools";

function renderClaudeSettings(_config: ResolvedConfig): string {
  const command = BINARY_NAME;
  const settings: ClaudeSettings = {
    permissions: { deny: collectDenyGlobs(ALL_RULE_GROUPS) },
    hooks: {
      PreToolUse: [
        {
          matcher: "Bash|Edit|Write|NotebookEdit|Read",
          hooks: [{ type: "command", command, timeout: HOOK_TIMEOUT_SECONDS }],
        },
      ],
      PostToolUse: [
        {
          matcher: "Edit|Write|NotebookEdit",
          hooks: [{ type: "command", command, timeout: HOOK_TIMEOUT_SECONDS }],
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
