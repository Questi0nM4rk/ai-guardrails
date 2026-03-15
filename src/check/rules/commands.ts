import { recurseRule } from "@/check/builder-cmd";
import {
  ALL_RULE_GROUPS,
  collectCommandRules,
  collectDenyGlobs,
} from "@/check/rules/groups";
import type { CommandRule } from "@/check/types";

export const COMMAND_RULES: CommandRule[] = [
  recurseRule(),
  ...collectCommandRules(ALL_RULE_GROUPS),
];

/**
 * Claude settings permissions.deny glob patterns used in .claude/settings.json
 * to block dangerous bash commands at the Claude tool-use layer.
 * These are a second line of defence alongside the engine rules at hook runtime.
 */
export const DANGEROUS_DENY_GLOBS: string[] = collectDenyGlobs(ALL_RULE_GROUPS);
