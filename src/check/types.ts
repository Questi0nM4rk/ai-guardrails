export type CheckDecision = "allow" | "ask" | "deny";

/** Rule-side decisions never include "allow" — a rule that didn't fire returns
 *  no decision; "allow" is only meaningful as the absence-of-match result. */
export type RuleDecision = "ask" | "deny";

export type CheckResult =
  | { decision: "allow" }
  | { decision: "ask"; reason: string }
  | { decision: "deny"; reason: string };

export type ToolEvent =
  | { type: "bash"; command: string }
  | { type: "write"; path: string }
  | { type: "read"; path: string };

export interface CallRule {
  kind: "call";
  cmd: string;
  sub?: string;
  flags?: string[];
  noFlags?: string[];
  args?: string[]; // all of these must appear in non-flag args
  hasDdash?: boolean;
  decision: RuleDecision;
  reason: string;
}

export interface PipeRule {
  kind: "pipe";
  from: string[];
  into: string[];
  decision: RuleDecision;
  reason: string;
}

export interface RedirectRule {
  kind: "redirect";
  pathPattern?: RegExp;
  decision: RuleDecision;
  reason: string;
}

export type CommandRule = CallRule | PipeRule | RedirectRule;

export interface PathRule {
  kind: "path";
  event: "write" | "read" | "both";
  pattern: RegExp;
  decision: RuleDecision;
  reason: string;
}

export interface RuleGroup {
  readonly id: string;
  readonly name: string;
  readonly commandRules: readonly CommandRule[];
  readonly denyGlobs: readonly string[];
}

export interface RuleSet {
  readonly commandRules: readonly CommandRule[];
  readonly pathRules: readonly PathRule[];
}

export interface HooksConfig {
  managedFiles?: string[];
  managedPaths?: string[];
  protectedReadPaths?: string[];
  disabledGroups?: string[];
}
