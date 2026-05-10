import type { CallRule, PipeRule, RedirectRule, RuleDecision } from "@/check/types";

export function callRule(
  cmd: string,
  opts: {
    sub?: string;
    flags?: string[];
    noFlags?: string[];
    args?: string[];
    hasDdash?: boolean;
    decision?: RuleDecision;
    reason: string;
  }
): CallRule {
  return { kind: "call", cmd, decision: opts.decision ?? "ask", ...opts };
}

export function pipeRule(
  from: string[],
  into: string[],
  reason: string,
  decision: RuleDecision = "ask"
): PipeRule {
  return { kind: "pipe", from, into, decision, reason };
}

export function redirectRule(
  reason: string,
  opts: { pathPattern?: RegExp; decision?: RuleDecision } = {}
): RedirectRule {
  return { kind: "redirect", decision: opts.decision ?? "ask", reason, ...opts };
}
