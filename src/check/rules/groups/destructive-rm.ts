import type { HookModule } from "@questi0nm4rk/hook-kit";
import { cmd, createModule } from "@questi0nm4rk/hook-kit";

const LABEL = "[ai-guardrails]";

export const destructiveRmModule: HookModule = createModule(
  {
    id: "destructive-rm",
    name: "Destructive rm",
    events: ["PreToolUse"],
    matchers: ["Bash"],
  },
  [
    cmd("rm")
      .withFlag("--recursive")
      .withFlag("--force")
      .escalate("rm with --recursive and --force flags", LABEL),
  ]
);

export const destructiveRmDenyGlobs = [
  "Bash(rm -rf *)",
  "Bash(rm -fr *)",
  "Bash(sudo rm -rf *)",
  "Bash(sudo rm -fr *)",
] as const;
