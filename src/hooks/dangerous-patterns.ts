import type { ParseEntry } from "shell-quote";
import { parse } from "shell-quote";

// Commands whose -c argument is itself a shell script and must be re-checked
const INLINE_SCRIPT_CMDS = new Set(["bash", "sh", "dash", "zsh", "ksh"]);

/** True if args contains a short flag with the given character (e.g. -rf contains r and f) */
function hasShortFlag(args: string[], char: string): boolean {
  return args.some((a) => a.startsWith("-") && !a.startsWith("--") && a.includes(char));
}

/** Unwrap a sudo/doas prefix so we check the real command */
function unwrapWrapper(cmd: string, args: string[]): { cmd: string; args: string[] } {
  if (cmd !== "sudo" && cmd !== "doas") return { cmd, args };
  // skip option flags (-u user, -E, etc.) to find the real command
  const idx = args.findIndex((a) => !a.startsWith("-"));
  if (idx === -1 || args[idx] === undefined) return { cmd, args };
  return { cmd: args[idx], args: args.slice(idx + 1) };
}

/**
 * Split shell-quote tokens into individual sub-commands, one array per command.
 * Splits on any shell operator (;  &&  ||  |  &).
 */
function splitSubCmds(tokens: ParseEntry[]): string[][] {
  const result: string[][] = [];
  let current: string[] = [];
  for (const tok of tokens) {
    if (typeof tok !== "string") {
      if (current.length > 0) {
        result.push(current);
        current = [];
      }
    } else {
      current.push(tok);
    }
  }
  if (current.length > 0) result.push(current);
  return result;
}

const PIPE_SHELLS = new Set([
  "bash",
  "sh",
  "dash",
  "zsh",
  "ksh",
  "csh",
  "tcsh",
  "fish",
]);

/**
 * Detect dangerous pipe sequences: curl/wget piped directly into any shell.
 * Returns a reason string or null.
 */
function checkPipes(tokens: ParseEntry[]): string | null {
  let prevWasPipe = false;
  let prevCmd = "";
  for (const tok of tokens) {
    if (typeof tok === "object" && "op" in tok) {
      prevWasPipe = tok.op === "|";
    } else if (typeof tok === "string") {
      if (prevWasPipe && PIPE_SHELLS.has(tok)) {
        return `${prevCmd} | ${tok} (remote code execution)`;
      }
      prevCmd = tok;
      prevWasPipe = false;
    }
  }
  return null;
}

/**
 * Check a single parsed sub-command (already split by shell operators) for
 * dangerous operations. Returns a human-readable reason or null.
 */
function checkSubCmd(rawCmd: string, rawArgs: string[]): string | null {
  const { cmd, args } = unwrapWrapper(rawCmd, rawArgs);

  if (cmd === "rm") {
    const hasR = hasShortFlag(args, "r") || args.includes("--recursive");
    const hasF = hasShortFlag(args, "f") || args.includes("--force");
    if (hasR && hasF) return "rm with -r and -f flags";
  }

  if (cmd === "git") {
    const sub = args[0];
    const rest = args.slice(1);

    if (sub === "push") {
      const hasForce = rest.includes("--force") || hasShortFlag(rest, "f");
      const hasLease = rest.some((a) => a.startsWith("--force-with-lease"));
      if (hasForce && !hasLease) return "git push --force";
    }
    if (sub === "reset" && rest.includes("--hard")) return "git reset --hard";
    if (sub === "checkout" && rest.includes("--"))
      return "git checkout -- (discard changes)";
    if (sub === "restore" && rest.includes("--"))
      return "git restore -- (discard changes)";
    if (sub === "clean" && (hasShortFlag(rest, "f") || rest.includes("--force")))
      return "git clean --force";
    if (sub === "commit") {
      if (rest.includes("--no-verify") || hasShortFlag(rest, "n"))
        return "git commit --no-verify";
    }
    if (sub === "branch") {
      const forceDelete =
        rest.some((a) => a.startsWith("-") && !a.startsWith("--") && a.includes("D")) ||
        (rest.includes("--delete") && rest.includes("--force")) ||
        (hasShortFlag(rest, "d") && rest.includes("--force"));
      if (forceDelete) return "git branch --force-delete";
    }
  }

  if (
    cmd === "chmod" &&
    (hasShortFlag(args, "R") || args.includes("--recursive")) &&
    (args.includes("777") || args.includes("a+rwx"))
  ) {
    return "chmod -R 777";
  }

  // bash/sh/eval: recurse into the -c argument (one level deep)
  if (INLINE_SCRIPT_CMDS.has(cmd) || cmd === "eval" || cmd === "exec") {
    const cIdx = args.indexOf("-c");
    const inline = cIdx !== -1 ? args[cIdx + 1] : cmd === "eval" ? args[0] : null;
    if (inline) return checkCommand(inline);
  }

  return null;
}

/**
 * Check a bash command string for dangerous operations.
 *
 * Uses shell-quote to tokenize — quoted strings become single opaque tokens, so
 * `git commit -m "rm -rf stuff"` does NOT trigger the rm check. The commit message
 * is one token in arg position, never inspected as a command.
 *
 * Returns a human-readable reason string if dangerous, null if safe.
 */
export function checkCommand(command: string): string | null {
  let tokens: ParseEntry[];
  try {
    tokens = parse(command);
  } catch {
    return null; // unparsable — let it through, deny globs cover obvious cases
  }

  const pipeReason = checkPipes(tokens);
  if (pipeReason) return pipeReason;

  for (const subCmd of splitSubCmds(tokens)) {
    const [cmd, ...args] = subCmd;
    if (!cmd) continue;
    const reason = checkSubCmd(cmd, args);
    if (reason) return reason;
  }

  return null;
}

/**
 * Claude settings permissions.deny glob patterns used in .claude/settings.json
 * to block dangerous bash commands at the Claude tool-use layer.
 * These are a second line of defence alongside checkCommand() at hook runtime.
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
