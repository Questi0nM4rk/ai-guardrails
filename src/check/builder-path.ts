import type { CheckDecision, PathRule } from "@/check/types";

export function pathRule(
  pattern: RegExp,
  event: "write" | "read" | "both",
  reason: string,
  decision: CheckDecision = "ask"
): PathRule {
  return { kind: "path", pattern, event, decision, reason };
}

export function protectWrite(pattern: RegExp, reason: string): PathRule {
  return pathRule(pattern, "write", reason, "ask");
}

export function protectRead(pattern: RegExp, reason: string): PathRule {
  return pathRule(pattern, "read", reason, "ask");
}
