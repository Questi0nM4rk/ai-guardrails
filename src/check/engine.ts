import type { ShellFile } from "@questi0nm4rk/shell-ast";
import { findCalls, parse } from "@questi0nm4rk/shell-ast";
import { unwrapCall } from "@questi0nm4rk/shell-ast/semantic";
import {
  checkRedirectsAgainstPathRules,
  checkWriteArgCommands,
  extractInlineScript,
  findPipeViolations,
  hasDdash,
  hasWriteRedirect,
} from "@/check/engine-helpers";
import { expandFlags, hasFlag } from "@/check/flag-aliases";
import type {
  CheckResult,
  CommandRule,
  PathRule,
  RuleSet,
  ToolEvent,
} from "@/check/types";

const INLINE_SHELL_CMDS = new Set(["bash", "sh", "dash", "zsh", "ksh", "eval", "exec"]);
const MAX_RECURSE_DEPTH = 5;

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
  if (depth > MAX_RECURSE_DEPTH)
    return {
      decision: "ask",
      reason: "inline script nesting too deep to inspect safely",
    };
  let ast: ShellFile;
  try {
    ast = await parse(command);
  } catch {
    return { decision: "allow" };
  }

  for (const rule of rules) {
    if (rule.kind === "redirect" && hasWriteRedirect(ast, rule.pathPattern)) {
      return { decision: rule.decision, reason: rule.reason };
    }
  }

  const redirectResult = checkRedirectsAgainstPathRules(ast, pathRules);
  if (redirectResult !== null) return redirectResult;

  // Pipe detection via AST BinaryCmd nodes — avoids false positives from &&/|| adjacency
  const pipeResult = findPipeViolations(ast, rules);
  if (pipeResult !== null) return pipeResult;

  const calls = findCalls(ast);

  // Check tee/cp/mv/sed-i argument destinations against path rules
  const writeArgResult = checkWriteArgCommands(calls, pathRules, evaluatePath);
  if (writeArgResult !== null) return writeArgResult;

  for (let i = 0; i < calls.length; i++) {
    const call = calls[i];
    if (call === undefined) continue;
    const unwrapped = unwrapCall(call);
    if (unwrapped === null) continue;
    const expanded = expandFlags(unwrapped.flags);

    for (const rule of rules) {
      if (rule.kind === "recurse" && INLINE_SHELL_CMDS.has(unwrapped.cmd)) {
        const inline = extractInlineScript(unwrapped);
        if (inline !== null) {
          const result = await evaluateCommand(inline, rules, pathRules, depth + 1);
          if (result.decision !== "allow") return result;
        }
      }

      if (rule.kind === "call" && rule.cmd === unwrapped.cmd) {
        if (rule.sub !== undefined && unwrapped.args[0] !== rule.sub) continue;
        const allFlagsPresent = (rule.flags ?? []).every((f) => hasFlag(expanded, f));
        const noFlagPresent = (rule.noFlags ?? []).every((f) => !hasFlag(expanded, f));
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

export function evaluatePath(
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
