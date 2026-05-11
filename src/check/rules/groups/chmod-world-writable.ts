import type { HookModule } from "@questi0nm4rk/hook-kit";
import { cmd, createModule } from "@questi0nm4rk/hook-kit";

const LABEL = "[ai-guardrails]";

export const chmodWorldWritableModule: HookModule = createModule(
  {
    id: "chmod-world-writable",
    name: "Chmod world-writable",
    events: ["PreToolUse"],
    matchers: ["Bash"],
  },
  [
    cmd("chmod")
      .withFlag("--recursive")
      .argIncludes("777")
      .escalate("chmod --recursive 777 (world-writable recursive)", LABEL),
    cmd("chmod")
      .withFlag("--recursive")
      .argIncludes("a+rwx")
      .escalate("chmod --recursive a+rwx (world-writable recursive)", LABEL),
  ]
);

export const chmodWorldWritableDenyGlobs = [
  "Bash(chmod -R 777*)",
  "Bash(chmod -R a+rwx*)",
] as const;
