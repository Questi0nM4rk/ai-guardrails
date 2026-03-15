import { callRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

export const destructiveRmGroup: RuleGroup = {
  id: "destructive-rm",
  name: "Destructive rm",
  commandRules: [
    callRule("rm", {
      flags: ["--recursive", "--force"],
      reason: "rm with --recursive and --force flags",
    }),
  ],
  denyGlobs: [
    "Bash(rm -rf *)",
    "Bash(rm -fr *)",
    "Bash(sudo rm -rf*)",
    "Bash(sudo rm -fr*)",
  ],
};
