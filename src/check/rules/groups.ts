import { chmodWorldWritableGroup } from "@/check/rules/groups/chmod-world-writable";
import { destructiveRmGroup } from "@/check/rules/groups/destructive-rm";
import { gitBypassHooksGroup } from "@/check/rules/groups/git-bypass-hooks";
import { gitDestructiveGroup } from "@/check/rules/groups/git-destructive";
import { gitForcePushGroup } from "@/check/rules/groups/git-force-push";
import { remoteCodeExecGroup } from "@/check/rules/groups/remote-code-exec";
import type { CommandRule, RuleGroup } from "@/check/types";

export const ALL_RULE_GROUPS: readonly RuleGroup[] = [
  destructiveRmGroup,
  gitForcePushGroup,
  gitDestructiveGroup,
  gitBypassHooksGroup,
  chmodWorldWritableGroup,
  remoteCodeExecGroup,
] as const;

/** Collect all command rules from the given groups. */
export function collectCommandRules(groups: readonly RuleGroup[]): CommandRule[] {
  return groups.flatMap((g) => g.commandRules);
}

/** Collect all deny globs from the given groups. */
export function collectDenyGlobs(groups: readonly RuleGroup[]): string[] {
  return groups.flatMap((g) => g.denyGlobs);
}
