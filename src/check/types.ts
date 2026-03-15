export type CheckDecision = "allow" | "ask" | "deny";

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
  decision: CheckDecision;
  reason: string;
}

export interface PipeRule {
  kind: "pipe";
  from: string[];
  into: string[];
  decision: CheckDecision;
  reason: string;
}

export interface RedirectRule {
  kind: "redirect";
  pathPattern?: RegExp;
  decision: CheckDecision;
  reason: string;
}

export interface RecurseRule {
  kind: "recurse";
}

export type CommandRule = CallRule | PipeRule | RedirectRule | RecurseRule;

export interface PathRule {
  kind: "path";
  event: "write" | "read" | "both";
  pattern: RegExp;
  decision: CheckDecision;
  reason: string;
}

export interface RuleGroup {
  id: string;
  name: string;
  commandRules: CommandRule[];
  denyGlobs: string[];
}

export interface RuleSet {
  commandRules: CommandRule[];
  pathRules: PathRule[];
}

export interface HooksConfig {
  managedFiles?: string[];
  managedPaths?: string[];
  protectedReadPaths?: string[];
  disabledGroups?: string[];
}
