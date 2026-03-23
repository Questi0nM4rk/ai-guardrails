import { askYesNo } from "@/init/prompt";
import type { InitCategory, InitContext, InitModule } from "@/init/types";

const CATEGORY_ORDER: readonly InitCategory[] = [
  "profile",
  "language-config",
  "universal-config",
  "hooks",
  "agent",
  "ci",
  "tools",
  "baseline",
];

const CATEGORY_LABELS: Record<InitCategory, string> = {
  profile: "Profile & Config",
  "language-config": "Language Configs",
  "universal-config": "Universal Configs",
  hooks: "Hooks",
  agent: "Agent Instructions",
  ci: "CI Pipeline",
  tools: "Tool Installation",
  baseline: "Baseline",
};

/**
 * Run the interactive wizard for init. Prompts the user for each applicable
 * module, grouped by category in display order.
 *
 * Returns a selections map: module id → true/false.
 */
export async function runWizard(
  ctx: InitContext,
  modules: readonly InitModule[]
): Promise<Map<string, boolean>> {
  const applicable = await filterApplicable(modules, ctx);

  if (applicable.length === 0) {
    return new Map();
  }

  const grouped = groupByCategory(applicable);
  const selections = new Map<string, boolean>();

  for (const category of CATEGORY_ORDER) {
    const categoryModules = grouped.get(category);
    if (categoryModules === undefined || categoryModules.length === 0) continue;

    ctx.console.info(`\n── ${CATEGORY_LABELS[category]} ──`);

    for (const mod of categoryModules) {
      const question = `${mod.name}: ${mod.description}`;
      const selected = await askYesNo(ctx.createReadline, question, mod.defaultEnabled);
      selections.set(mod.id, selected);
    }
  }

  return selections;
}

async function filterApplicable(
  modules: readonly InitModule[],
  ctx: InitContext
): Promise<InitModule[]> {
  const results = await Promise.all(
    modules.map(async (mod) => ({ mod, applicable: await mod.detect(ctx) }))
  );
  return results.filter((r) => r.applicable).map((r) => r.mod);
}

function groupByCategory(
  modules: readonly InitModule[]
): Map<InitCategory, InitModule[]> {
  const grouped = new Map<InitCategory, InitModule[]>();
  for (const mod of modules) {
    const existing = grouped.get(mod.category);
    if (existing !== undefined) {
      existing.push(mod);
    } else {
      grouped.set(mod.category, [mod]);
    }
  }
  return grouped;
}
