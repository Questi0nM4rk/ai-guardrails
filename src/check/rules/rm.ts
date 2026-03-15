import { callRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

export const RM_GROUP: RuleGroup = {
  id: "rm",
  label: "rm — recursive force delete",
  commandRules: [
    callRule("rm", {
      flags: ["-r", "-f"],
      reason: "rm with recursive and force flags",
    }),
  ],
  denyGlobs: [
    "Bash(rm -rf *)",
    "Bash(rm -fr *)",
    "Bash(sudo rm -rf*)",
    "Bash(sudo rm -fr*)",
  ],
} as const;
