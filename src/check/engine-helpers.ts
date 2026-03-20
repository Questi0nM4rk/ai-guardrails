import type {
  BinaryCmd,
  CallExprNode,
  ShellFile,
  Stmt,
  Word,
} from "@questi0nm4rk/shell-ast";
import { walk, wordToLit } from "@questi0nm4rk/shell-ast";
import type { UnwrappedCall } from "@questi0nm4rk/shell-ast/semantic";
import { unwrapCall } from "@questi0nm4rk/shell-ast/semantic";
import type { CheckResult, CommandRule, PathRule } from "@/check/types";

const WRITE_OPS = new Set([">", ">>", ">|", "&>", "&>>"]);

/** Last non-flag arg is the write destination (cp src dst, mv src dst). */
const LAST_ARG_WRITE_CMDS = new Set(["cp", "mv"]);
/** All non-flag args are write destinations (tee file1 file2). */
const ALL_ARGS_WRITE_CMDS = new Set(["tee"]);

/** True if the call includes `--` in its raw arg list. */
export function hasDdash(call: CallExprNode): boolean {
  return call.args.some((w) => wordToLit(w) === "--");
}

/** True if the AST contains any write redirect matching pathPattern. */
export function hasWriteRedirect(ast: ShellFile, pathPattern?: RegExp): boolean {
  let found = false;
  walk(ast, {
    Stmt(node: Stmt) {
      if (found) return;
      for (const redir of node.redirs) {
        if (!WRITE_OPS.has(redir.op)) continue;
        if (pathPattern === undefined) {
          found = true;
          return;
        }
        const target = wordToLit(redir.word);
        if (target !== null && pathPattern.test(target)) {
          found = true;
          return;
        }
      }
    },
  });
  return found;
}

/** Checks redirect targets against path rules — catches `cmd > .env` patterns. */
export function checkRedirectsAgainstPathRules(
  ast: ShellFile,
  pathRules: readonly PathRule[]
): CheckResult | null {
  let result: CheckResult | null = null;
  walk(ast, {
    Stmt(node: Stmt) {
      if (result !== null) return;
      for (const redir of node.redirs) {
        if (!WRITE_OPS.has(redir.op)) continue;
        const target = wordToLit(redir.word);
        if (target === null) continue;
        for (const rule of pathRules) {
          if (
            (rule.event === "both" || rule.event === "write") &&
            rule.pattern.test(target)
          ) {
            result = { decision: rule.decision, reason: rule.reason };
            return;
          }
        }
      }
    },
  });
  return result;
}

/** Walk BinaryCmd pipe nodes to detect actual `from | into` patterns. */
export function findPipeViolations(
  ast: ShellFile,
  rules: readonly CommandRule[]
): CheckResult | null {
  let result: CheckResult | null = null;
  walk(ast, {
    BinaryCmd(node: BinaryCmd) {
      if (result !== null) return;
      if (node.op !== "|" && node.op !== "|&") return;
      const leftCmd = stmtToCmd(node.x);
      const rightCmd = stmtToCmd(node.y);
      if (leftCmd === null || rightCmd === null) return;
      for (const rule of rules) {
        if (
          rule.kind === "pipe" &&
          rule.from.includes(leftCmd) &&
          rule.into.includes(rightCmd)
        ) {
          result = { decision: rule.decision, reason: rule.reason };
          return;
        }
      }
    },
  });
  return result;
}

function stmtToCmd(stmt: Stmt): string | null {
  const cmd = stmt.cmd;
  if (cmd === null || cmd.type !== "CallExpr") return null;
  const unwrapped = unwrapCall(cmd);
  return unwrapped?.cmd ?? null;
}

/** Checks tee/cp/mv/sed-i argument destinations against path rules. */
export function checkWriteArgCommands(
  calls: CallExprNode[],
  pathRules: readonly PathRule[],
  evaluatePath: (
    path: string,
    event: "write" | "read",
    rules: readonly PathRule[]
  ) => CheckResult
): CheckResult | null {
  for (const call of calls) {
    const unwrapped = unwrapCall(call);
    if (unwrapped === null) continue;
    const writePaths: string[] = [];

    if (ALL_ARGS_WRITE_CMDS.has(unwrapped.cmd)) {
      writePaths.push(...unwrapped.args.filter((a) => !a.startsWith("-")));
    } else if (LAST_ARG_WRITE_CMDS.has(unwrapped.cmd)) {
      const nonFlags = unwrapped.args.filter((a) => !a.startsWith("-"));
      const last = nonFlags[nonFlags.length - 1];
      if (last !== undefined) writePaths.push(last);
    } else if (
      unwrapped.cmd === "sed" &&
      unwrapped.flags.some((f) => f.startsWith("-i"))
    ) {
      // sed -i 's/.../.../' file — last non-flag arg is target
      const nonFlags = unwrapped.args.filter((a) => !a.startsWith("-"));
      const last = nonFlags[nonFlags.length - 1];
      if (last !== undefined) writePaths.push(last);
    }

    for (const writePath of writePaths) {
      const res = evaluatePath(writePath, "write", pathRules);
      if (res.decision !== "allow") return res;
    }
  }
  return null;
}

/** Extract the inline script from `bash -c '...'` / `eval '...'`. */
export function extractInlineScript(unwrapped: UnwrappedCall): string | null {
  if (unwrapped.flags.includes("-c")) {
    const rawArgs = unwrapped.raw.args;
    let seenDashC = false;
    for (const word of rawArgs) {
      const lit = wordToLit(word);
      if (lit === "-c") {
        seenDashC = true;
        continue;
      }
      if (seenDashC) {
        return wordToScript(word);
      }
    }
  }
  if (unwrapped.cmd === "eval") {
    // eval concatenates all args with spaces and re-parses as shell syntax (POSIX)
    const args = unwrapped.raw.args.slice(1);
    if (args.length === 0) return null;
    const parts = args.map(wordToScript);
    if (parts.some((p) => p === null)) return null;
    return parts.filter((p): p is string => p !== null).join(" ");
  }
  if (unwrapped.cmd === "exec") {
    // exec replaces the process — does not re-parse shell syntax; inspect first arg only
    const firstRawArg = unwrapped.raw.args[1];
    return firstRawArg !== undefined ? wordToScript(firstRawArg) : null;
  }
  return null;
}

/** Resolve a Word to a plain string, handling Lit and SglQuoted parts. */
function wordToScript(word: Word): string | null {
  const chunks: string[] = [];
  for (const part of word.parts) {
    if (part.type === "Lit") {
      chunks.push(part.value);
    } else if (part.type === "SglQuoted") {
      chunks.push(part.value);
    } else {
      return null;
    }
  }
  return chunks.length > 0 ? chunks.join("") : null;
}
