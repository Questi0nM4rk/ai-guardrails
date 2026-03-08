import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";

function renderMarkdownlintJsonc(_config: ResolvedConfig): string {
  // Note: no hash header — jsonc comments would be stripped by JSON parsers
  return `{
  "default": true,
  "MD013": { "line_length": 120, "tables": false, "code_blocks": false },
  "MD033": false,
  "MD041": false
}
`;
}

export const markdownlintGenerator: ConfigGenerator = {
  id: "markdownlint",
  configFile: ".markdownlint.jsonc",
  generate(config: ResolvedConfig): string {
    return renderMarkdownlintJsonc(config);
  },
};
