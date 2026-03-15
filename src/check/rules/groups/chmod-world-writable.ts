import { callRule } from "@/check/builder-cmd";
import type { RuleGroup } from "@/check/types";

export const chmodWorldWritableGroup: RuleGroup = {
  id: "chmod-world-writable",
  name: "Chmod world-writable",
  commandRules: [
    callRule("chmod", {
      flags: ["--recursive"],
      args: ["777"],
      reason: "chmod --recursive 777 (world-writable recursive)",
    }),
    callRule("chmod", {
      flags: ["--recursive"],
      args: ["a+rwx"],
      reason: "chmod --recursive a+rwx (world-writable recursive)",
    }),
  ],
  denyGlobs: ["Bash(chmod -R 777*)"],
};
