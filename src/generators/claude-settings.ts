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
  hooks: { PreToolUse: MatcherEntry[]; PostToolUse: MatcherEntry[] };
}

// 60s matches CC's default hook timeout and stays under the 120s default
// Bash tool budget. Hooks that block longer than the agent's tool timeout
// orphan when the agent abandons the call. See SPEC-014.
const HOOK_TIMEOUT_SECONDS = 60;
const BINARY_NAME = "ai-guardrails-hk-cc-tools";

function renderClaudeSettings(_config: ResolvedConfig): string {
  const command = BINARY_NAME;
  // BUG-009: dropped the hardcoded `permissions.deny` list. CC's pattern DSL
  // is strictly weaker than the hook's shell-AST matcher (no flag aliasing,
  // no `--` end-of-options handling, no sudo unwrap) so shipping both creates
  // two sources of truth that don't agree. The hook is the source of truth;
  // permissions.deny was duplicating it poorly. Users with extra-paranoid
  // setups can still add `permissions.deny` patterns to their own
  // `.claude/settings.local.json` — those merge on top.
  const settings: ClaudeSettings = {
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
