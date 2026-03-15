import { pipeRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

const PIPE_SHELLS = [
  "bash",
  "sh",
  "dash",
  "zsh",
  "ksh",
  "csh",
  "tcsh",
  "fish",
] as const;
const CURL_WGET = ["curl", "wget"] as const;

export const remoteCodeExecGroup: RuleGroup = {
  id: "remote-code-exec",
  name: "Remote code execution",
  commandRules: [
    pipeRule(
      [...CURL_WGET],
      [...PIPE_SHELLS],
      "curl/wget piped into a shell (remote code execution)"
    ),
  ],
  denyGlobs: [
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
  ],
};
