import { callRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

export const gitBypassHooksGroup: RuleGroup = {
  id: "git-bypass-hooks",
  name: "Git bypass hooks",
  commandRules: [
    callRule("git", {
      sub: "commit",
      flags: ["--no-verify"],
      reason: "git commit --no-verify (bypasses hooks)",
    }),
  ],
  denyGlobs: ["Bash(git commit --no-verify*)", "Bash(git commit -n *)"],
};
