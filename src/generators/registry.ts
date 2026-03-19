import { agentRulesGenerator } from "@/generators/agent-rules";
import { biomeGenerator } from "@/generators/biome";
import { claudeSettingsGenerator } from "@/generators/claude-settings";
import { codespellGenerator } from "@/generators/codespell";
import { editorconfigGenerator } from "@/generators/editorconfig";
import { lefthookGenerator } from "@/generators/lefthook";
import { markdownlintGenerator } from "@/generators/markdownlint";
import { ruffGenerator } from "@/generators/ruff";
import type { ConfigGenerator } from "@/generators/types";

/** All built-in config generators */
export const ALL_GENERATORS: readonly ConfigGenerator[] = [
  ruffGenerator,
  biomeGenerator,
  editorconfigGenerator,
  markdownlintGenerator,
  codespellGenerator,
  lefthookGenerator,
  claudeSettingsGenerator,
  agentRulesGenerator,
];

/** Filter generators to those applicable for the given active language IDs */
export function applicableGenerators(
  activeLanguageIds: ReadonlySet<string>
): readonly ConfigGenerator[] {
  return ALL_GENERATORS.filter(
    (g) =>
      g.languages === undefined || g.languages.some((id) => activeLanguageIds.has(id))
  );
}
