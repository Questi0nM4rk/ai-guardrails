import type { HookModule } from "@questi0nm4rk/hook-kit";
import { createModule } from "@questi0nm4rk/hook-kit";
import { suppressCommentsRule } from "@/check/rules/suppress-comments";
import { buildAllModules, loadHookConfig } from "@/check/ruleset";

const modules: HookModule[] = [
  ...buildAllModules(loadHookConfig()),
  createModule(
    {
      id: "suppress-comments",
      name: "Suppress unjustified linter-disable comments",
      events: ["PostToolUse"],
      matchers: ["Edit", "Write", "NotebookEdit"],
    },
    [suppressCommentsRule()]
  ),
];

export default modules;
