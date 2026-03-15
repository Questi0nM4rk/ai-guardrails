import { CHMOD_GROUP } from "@/check/rules/chmod";
import { GIT_DESTRUCTIVE_GROUP } from "@/check/rules/git-destructive";
import { GIT_PUSH_GROUP } from "@/check/rules/git-push";
import { GIT_WORKFLOW_GROUP } from "@/check/rules/git-workflow";
import { REMOTE_EXEC_GROUP } from "@/check/rules/remote-exec";
import { RM_GROUP } from "@/check/rules/rm";
import type { CommandRule, RuleGroup } from "@/check/types";

export const ALL_RULE_GROUPS: readonly RuleGroup[] = [
  GIT_PUSH_GROUP,
  GIT_DESTRUCTIVE_GROUP,
  GIT_WORKFLOW_GROUP,
  RM_GROUP,
  CHMOD_GROUP,
  REMOTE_EXEC_GROUP,
] as const;

export function collectCommandRules(
  groups: readonly RuleGroup[]
): readonly CommandRule[] {
  return groups.flatMap((g) => [...g.commandRules]);
}

export function collectDenyGlobs(groups: readonly RuleGroup[]): readonly string[] {
  return groups.flatMap((g) => [...g.denyGlobs]);
}

/** Backward-compatible exports — same shape as the old commands.ts */
export const COMMAND_RULES: readonly CommandRule[] =
  collectCommandRules(ALL_RULE_GROUPS);
export const DANGEROUS_DENY_GLOBS: readonly string[] =
  collectDenyGlobs(ALL_RULE_GROUPS);
