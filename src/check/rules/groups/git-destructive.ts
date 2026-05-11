import type { HookModule } from "@questi0nm4rk/hook-kit";
import { cmd, createModule } from "@questi0nm4rk/hook-kit";

const LABEL = "[ai-guardrails]";

export const gitDestructiveModule: HookModule = createModule(
  {
    id: "git-destructive",
    name: "Git destructive operations",
    events: ["PreToolUse"],
    matchers: ["Bash"],
  },
  [
    cmd("git", "reset").withFlag("--hard").escalate("git reset --hard", LABEL),
    cmd("git", "checkout")
      .withDdash()
      .escalate("git checkout -- (discard working tree changes)", LABEL),
    cmd("git", "restore")
      .withDdash()
      .escalate("git restore -- (discard working tree changes)", LABEL),
    cmd("git", "clean").withFlag("--force").escalate("git clean --force", LABEL),
    cmd("git", "branch")
      .withFlag("--delete")
      .withFlag("--force")
      .escalate("git branch --delete --force (force delete)", LABEL),
  ]
);

export const gitDestructiveDenyGlobs = [
  "Bash(git reset --hard*)",
  "Bash(git checkout -- *)",
  "Bash(git restore -- *)",
  "Bash(git clean -f*)",
  "Bash(git clean --force*)",
  "Bash(git branch -D *)",
  "Bash(git branch --delete --force *)",
] as const;
