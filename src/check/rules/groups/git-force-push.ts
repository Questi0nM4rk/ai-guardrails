import type { HookModule } from "@questi0nm4rk/hook-kit";
import { cmd, createModule } from "@questi0nm4rk/hook-kit";

const LABEL = "[ai-guardrails]";

export const gitForcePushModule: HookModule = createModule(
  {
    id: "git-force-push",
    name: "Git force push",
    events: ["PreToolUse"],
    matchers: ["Bash"],
  },
  [
    cmd("git", "push")
      .withFlag("--force")
      .withoutFlag("--force-with-lease")
      .escalate("git push --force", LABEL),
  ]
);

export const gitForcePushDenyGlobs = [
  "Bash(git push --force)",
  "Bash(git push --force *)",
  "Bash(git push -f)",
  "Bash(git push -f *)",
] as const;
