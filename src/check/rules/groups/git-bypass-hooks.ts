import type { HookModule } from "@questi0nm4rk/hook-kit";
import { cmd, createModule } from "@questi0nm4rk/hook-kit";

const LABEL = "[ai-guardrails]";

export const gitBypassHooksModule: HookModule = createModule(
  {
    id: "git-bypass-hooks",
    name: "Git bypass hooks",
    events: ["PreToolUse"],
    matchers: ["Bash"],
  },
  [
    cmd("git", "commit")
      .withFlag("--no-verify")
      .escalate("git commit --no-verify (bypasses hooks)", LABEL),
    // -n is NOT aliased globally (means --dry-run for git push, --no-checkout for git clone).
    cmd("git", "commit")
      .withFlag("-n")
      .escalate("git commit -n (bypasses hooks)", LABEL),
  ]
);

export const gitBypassHooksDenyGlobs = [
  "Bash(git commit --no-verify*)",
  "Bash(git commit -n *)",
  "Bash(git commit -n)",
] as const;
