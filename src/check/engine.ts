import type { CallExprNode, ShellFile, Stmt, Word } from "@questi0nm4rk/shell-ast";
import { findCalls, parse, walk, wordToLit } from "@questi0nm4rk/shell-ast";
import type { UnwrappedCall } from "@questi0nm4rk/shell-ast/semantic";
import { unwrapCall } from "@questi0nm4rk/shell-ast/semantic";
import type {
  CheckResult,
  CommandRule,
  PathRule,
  RuleSet,
  ToolEvent,
} from "@/check/types";

const INLINE_SHELL_CMDS = new Set(["bash", "sh", "dash", "zsh", "ksh", "eval", "exec"]);
const MAX_RECURSE_DEPTH = 5;
const WRITE_OPS = new Set([">", ">>", ">|", "&>", "&>>"]);

export async function evaluate(
  event: ToolEvent,
  ruleset: RuleSet
): Promise<CheckResult> {
  if (event.type === "bash") {
    return evaluateCommand(event.command, ruleset.commandRules, ruleset.pathRules, 0);
  }
  return evaluatePath(event.path, event.type, ruleset.pathRules);
}

async function evaluateCommand(
  command: string,
  rules: CommandRule[],
  pathRules: PathRule[],
  depth: number
): Promise<CheckResult> {
  if (depth > MAX_RECURSE_DEPTH) return { decision: "allow" };
  let ast: ShellFile;
  try {
    ast = await parse(command);
  } catch {
    return { decision: "allow" };
  }

  const calls = findCalls(ast);

  for (const rule of rules) {
    if (rule.kind === "redirect" && hasWriteRedirect(ast, rule.pathPattern)) {
      return { decision: rule.decision, reason: rule.reason };
    }
  }

  // Check write redirect targets against path rules (a redirect is a write event)
  const redirectResult = checkRedirectsAgainstPathRules(ast, pathRules);
  if (redirectResult !== null) return redirectResult;

  for (let i = 0; i < calls.length; i++) {
    const call = calls[i];
    if (call === undefined) continue;
    const unwrapped = unwrapCall(call);
    if (unwrapped === null) continue;

    for (const rule of rules) {
      if (rule.kind === "pipe" && rule.into.includes(unwrapped.cmd) && i > 0) {
        const prevCall = calls[i - 1];
        if (prevCall !== undefined) {
          const prev = unwrapCall(prevCall);
          if (prev !== null && rule.from.includes(prev.cmd)) {
            return { decision: rule.decision, reason: rule.reason };
          }
        }
      }

      if (rule.kind === "recurse" && INLINE_SHELL_CMDS.has(unwrapped.cmd)) {
        const inline = extractInlineScript(unwrapped);
        if (inline !== null) {
          const result = await evaluateCommand(inline, rules, pathRules, depth + 1);
          if (result.decision !== "allow") return result;
        }
      }

      if (rule.kind === "call" && rule.cmd === unwrapped.cmd) {
        if (rule.sub !== undefined && unwrapped.args[0] !== rule.sub) continue;
        const flags = unwrapped.flags;
        const allFlagsPresent = (rule.flags ?? []).every((f) => flags.includes(f));
        const noFlagPresent = (rule.noFlags ?? []).every((f) => !flags.includes(f));
        const allArgsPresent = (rule.args ?? []).every((a) =>
          unwrapped.args.includes(a)
        );
        const ddashOk = rule.hasDdash === true ? hasDdash(call) : true;
        if (allFlagsPresent && noFlagPresent && allArgsPresent && ddashOk) {
          return { decision: rule.decision, reason: rule.reason };
        }
      }
    }
  }

  return { decision: "allow" };
}

function hasDdash(call: CallExprNode): boolean {
  return call.args.some((w) => wordToLit(w) === "--");
}

/**
 * Extract the inline script from `bash -c '...'` / `eval '...'`.
 * Uses raw CallExprNode args because `unwrapped.args` replaces quoted words
 * with the `"<dynamic>"` sentinel — resolved here via `wordToScript`.
 */
function extractInlineScript(unwrapped: UnwrappedCall): string | null {
  if (unwrapped.flags.includes("-c") || unwrapped.args.includes("-c")) {
    // Find the first raw arg word that follows the -c flag in the raw call
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
  if (unwrapped.cmd === "eval" || unwrapped.cmd === "exec") {
    const firstRawArg = unwrapped.raw.args[1];
    return firstRawArg !== undefined ? wordToScript(firstRawArg) : null;
  }
  return null;
}

/** Resolve a Word to a plain string, handling Lit and SglQuoted parts; null for dynamic content. */
function wordToScript(word: Word): string | null {
  const parts = word.parts;
  if (parts.length === 0) return null;
  const chunks: string[] = [];
  for (const part of parts) {
    if (part.type === "Lit") {
      chunks.push(part.value);
    } else if (part.type === "SglQuoted") {
      chunks.push(part.value);
    } else {
      return null;
    }
  }
  return chunks.join("");
}

function checkRedirectsAgainstPathRules(
  ast: ShellFile,
  pathRules: PathRule[]
): CheckResult | null {
  let result: CheckResult | null = null;
  walk(ast, {
    Stmt(node: Stmt) {
      for (const redir of node.redirs) {
        if (!WRITE_OPS.has(redir.op)) continue;
        const target = wordToLit(redir.hdoc ?? redir.word);
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

function hasWriteRedirect(ast: ShellFile, pathPattern?: RegExp): boolean {
  let found = false;
  walk(ast, {
    Stmt(node: Stmt) {
      for (const redir of node.redirs) {
        if (!WRITE_OPS.has(redir.op)) continue;
        if (pathPattern === undefined) {
          found = true;
          return;
        }
        const target = wordToLit(redir.hdoc ?? redir.word);
        if (target !== null && pathPattern.test(target)) {
          found = true;
          return;
        }
      }
    },
  });
  return found;
}

function evaluatePath(
  path: string,
  eventType: "write" | "read",
  rules: PathRule[]
): CheckResult {
  for (const rule of rules) {
    if (
      (rule.event === "both" || rule.event === eventType) &&
      rule.pattern.test(path)
    ) {
      return { decision: rule.decision, reason: rule.reason };
    }
  }
  return { decision: "allow" };
}
