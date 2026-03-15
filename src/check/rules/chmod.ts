import { callRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

export const CHMOD_GROUP: RuleGroup = {
  id: "chmod",
  label: "chmod — world-writable recursive",
  commandRules: [
    callRule("chmod", {
      flags: ["-R"],
      args: ["777"],
      reason: "chmod -R 777 (world-writable recursive)",
    }),
    callRule("chmod", {
      flags: ["-R"],
      args: ["a+rwx"],
      reason: "chmod -R a+rwx (world-writable recursive)",
    }),
  ],
  denyGlobs: ["Bash(chmod -R 777*)"],
} as const;
