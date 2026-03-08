import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import { withJsoncHashHeader } from "@/utils/hash";

function renderMarkdownlintJsonc(_config: ResolvedConfig): string {
    const body = `{
  "default": true,
  "MD013": { "line_length": 120, "tables": false, "code_blocks": false },
  "MD033": false,
  "MD040": false,
  "MD041": false,
  "MD060": false
}
`;
    return withJsoncHashHeader(body);
}

export const markdownlintGenerator: ConfigGenerator = {
    id: "markdownlint",
    configFile: ".markdownlint.jsonc",
    generate(config: ResolvedConfig): string {
        return renderMarkdownlintJsonc(config);
    },
};
