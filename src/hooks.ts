import type { HookModule } from "@questi0nm4rk/hook-kit";
import { createModule } from "@questi0nm4rk/hook-kit";
import { suppressCommentsRule } from "@/check/rules/suppress-comments";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { buildAllModules } from "@/check/to-hook-kit";

const LABEL = "[ai-guardrails]";

const ruleset = buildRuleSet(await loadHookConfig());

const modules: HookModule[] = [
  ...buildAllModules(ruleset, LABEL),
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
