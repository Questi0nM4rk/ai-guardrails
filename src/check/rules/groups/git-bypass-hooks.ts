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
    // -n is NOT aliased globally (it means --dry-run for git push, --no-checkout for git clone).
    // Explicit sub-scoped rule needed for git commit -n.
    callRule("git", {
      sub: "commit",
      flags: ["-n"],
      reason: "git commit -n (bypasses hooks)",
    }),
  ],
  denyGlobs: ["Bash(git commit --no-verify*)", "Bash(git commit -n *)"],
};
