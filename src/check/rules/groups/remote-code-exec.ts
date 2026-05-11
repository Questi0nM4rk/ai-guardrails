import type { HookModule } from "@questi0nm4rk/hook-kit";
import { createModule, pipe } from "@questi0nm4rk/hook-kit";

const LABEL = "[ai-guardrails]";

const PIPE_SHELLS = ["bash", "sh", "dash", "zsh", "ksh", "csh", "tcsh", "fish"];
const FETCHERS = ["curl", "wget"];

export const remoteCodeExecModule: HookModule = createModule(
  {
    id: "remote-code-exec",
    name: "Remote code execution",
    events: ["PreToolUse"],
    matchers: ["Bash"],
  },
  [
    pipe(FETCHERS, PIPE_SHELLS).escalate(
      "curl/wget piped into a shell (remote code execution)",
      LABEL
    ),
  ]
);

export const remoteCodeExecDenyGlobs = [
  "Bash(curl * | bash)",
  "Bash(curl * | sh)",
  "Bash(curl * | zsh)",
  "Bash(curl * | dash)",
  "Bash(curl * | ksh)",
  "Bash(wget * | bash)",
  "Bash(wget * | sh)",
  "Bash(wget * | zsh)",
  "Bash(wget * | dash)",
  "Bash(wget * | ksh)",
  "Bash(eval $(*))",
  "Bash(python -c*import os*system*)",
] as const;
