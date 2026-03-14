import { callRule, pipeRule, recurseRule } from "@/check/builder-cmd";
import type { CommandRule } from "@/check/types";

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

export const COMMAND_RULES: CommandRule[] = [
  recurseRule(),
  pipeRule(
    [...CURL_WGET],
    [...PIPE_SHELLS],
    "curl/wget piped into a shell (remote code execution)"
  ),
  callRule("rm", { flags: ["-r", "-f"], reason: "rm with -r and -f flags" }),
  callRule("rm", {
    flags: ["--recursive", "--force"],
    reason: "rm with --recursive and --force flags",
  }),
  callRule("git", {
    sub: "push",
    flags: ["--force"],
    noFlags: ["--force-with-lease"],
    reason: "git push --force",
  }),
  callRule("git", { sub: "push", flags: ["-f"], reason: "git push -f" }),
  callRule("git", { sub: "reset", flags: ["--hard"], reason: "git reset --hard" }),
  callRule("git", {
    sub: "checkout",
    hasDdash: true,
    reason: "git checkout -- (discard working tree changes)",
  }),
  callRule("git", {
    sub: "restore",
    hasDdash: true,
    reason: "git restore -- (discard working tree changes)",
  }),
  callRule("git", { sub: "clean", flags: ["-f"], reason: "git clean -f" }),
  callRule("git", { sub: "clean", flags: ["--force"], reason: "git clean --force" }),
  callRule("git", {
    sub: "commit",
    flags: ["--no-verify"],
    reason: "git commit --no-verify (bypasses hooks)",
  }),
  callRule("git", {
    sub: "commit",
    flags: ["-n"],
    reason: "git commit -n (bypasses hooks)",
  }),
  callRule("git", {
    sub: "branch",
    flags: ["-D"],
    reason: "git branch -D (force delete)",
  }),
  callRule("chmod", {
    flags: ["-R"],
    args: ["777"],
    reason: "chmod -R 777 (world-writable recursive)",
  }),
];

/**
 * Claude settings permissions.deny glob patterns used in .claude/settings.json
 * to block dangerous bash commands at the Claude tool-use layer.
 * These are a second line of defence alongside the engine rules at hook runtime.
 * Copied verbatim from src/hooks/dangerous-patterns.ts.
 */
export const DANGEROUS_DENY_GLOBS: string[] = [
  "Bash(git push --force)",
  "Bash(git push --force *)",
  "Bash(git push -f *)",
  "Bash(git reset --hard*)",
  "Bash(git checkout -- *)",
  "Bash(git restore -- *)",
  "Bash(git clean -f*)",
  "Bash(git clean --force*)",
  "Bash(git commit --no-verify*)",
  "Bash(git commit -n *)",
  "Bash(git branch -D *)",
  "Bash(rm -rf *)",
  "Bash(rm -fr *)",
  "Bash(sudo rm -rf*)",
  "Bash(sudo rm -fr*)",
  "Bash(chmod -R 777*)",
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
];
