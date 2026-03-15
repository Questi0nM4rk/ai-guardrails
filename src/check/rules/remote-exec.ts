import { pipeRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

/** Shells to match in pipe rules (AST-based detection). */
const PIPE_SHELLS = [
  "bash",
  "sh",
  "zsh",
  "dash",
  "ksh",
  "csh",
  "tcsh",
  "fish",
] as const;
const CURL_WGET = ["curl", "wget"] as const;

/**
 * Shells to include in deny globs (Claude settings.json layer).
 * Only the 5 most common POSIX-like shells — csh/tcsh/fish are rare enough
 * that the AST pipe rule alone is sufficient.
 */
const DENY_GLOB_SHELLS = ["bash", "sh", "zsh", "dash", "ksh"] as const;

function pipeDenyGlobs(from: readonly string[], into: readonly string[]): string[] {
  const globs: string[] = [];
  for (const f of from) {
    for (const i of into) {
      globs.push(`Bash(${f} * | ${i})`);
    }
  }
  return globs;
}

export const REMOTE_EXEC_GROUP: RuleGroup = {
  id: "remote-exec",
  label: "remote execution — curl/wget piped into shell",
  commandRules: [
    pipeRule(
      [...CURL_WGET],
      [...PIPE_SHELLS],
      "curl/wget piped into a shell (remote code execution)"
    ),
  ],
  denyGlobs: [
    ...pipeDenyGlobs(CURL_WGET, DENY_GLOB_SHELLS),
    "Bash(eval $(*))",
    "Bash(python -c*import os*system*)",
  ],
} as const;
