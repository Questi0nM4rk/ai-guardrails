import type { HookModule } from "@questi0nm4rk/hook-kit";
import {
  chmodWorldWritableDenyGlobs,
  chmodWorldWritableModule,
} from "@/check/rules/groups/chmod-world-writable";
import {
  destructiveRmDenyGlobs,
  destructiveRmModule,
} from "@/check/rules/groups/destructive-rm";
import {
  gitBypassHooksDenyGlobs,
  gitBypassHooksModule,
} from "@/check/rules/groups/git-bypass-hooks";
import {
  gitDestructiveDenyGlobs,
  gitDestructiveModule,
} from "@/check/rules/groups/git-destructive";
import {
  gitForcePushDenyGlobs,
  gitForcePushModule,
} from "@/check/rules/groups/git-force-push";
import {
  remoteCodeExecDenyGlobs,
  remoteCodeExecModule,
} from "@/check/rules/groups/remote-code-exec";

/** A logical AG rule group: one hook-kit module + the static deny globs that
 *  Claude Code's permissions.deny mirrors. */
export interface RuleGroup {
  readonly id: string;
  readonly module: HookModule;
  readonly denyGlobs: readonly string[];
}

export const ALL_RULE_GROUPS: readonly RuleGroup[] = [
  {
    id: "destructive-rm",
    module: destructiveRmModule,
    denyGlobs: destructiveRmDenyGlobs,
  },
  {
    id: "git-force-push",
    module: gitForcePushModule,
    denyGlobs: gitForcePushDenyGlobs,
  },
  {
    id: "git-destructive",
    module: gitDestructiveModule,
    denyGlobs: gitDestructiveDenyGlobs,
  },
  {
    id: "git-bypass-hooks",
    module: gitBypassHooksModule,
    denyGlobs: gitBypassHooksDenyGlobs,
  },
  {
    id: "chmod-world-writable",
    module: chmodWorldWritableModule,
    denyGlobs: chmodWorldWritableDenyGlobs,
  },
  {
    id: "remote-code-exec",
    module: remoteCodeExecModule,
    denyGlobs: remoteCodeExecDenyGlobs,
  },
] as const;

export function collectModules(groups: readonly RuleGroup[]): HookModule[] {
  return groups.map((g) => g.module);
}

export function collectDenyGlobs(groups: readonly RuleGroup[]): string[] {
  return groups.flatMap((g) => g.denyGlobs);
}

export const DANGEROUS_DENY_GLOBS: readonly string[] =
  collectDenyGlobs(ALL_RULE_GROUPS);
