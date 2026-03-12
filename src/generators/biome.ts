import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import { withJsoncHashHeader } from "@/utils/hash";

function renderBiomeJson(config: ResolvedConfig): string {
  const lineWidth = config.values.line_length ?? 100;
  const indentWidth = config.values.indent_width ?? 2;
  return JSON.stringify(
    {
      $schema: "https://biomejs.dev/schemas/2.4.6/schema.json",
      linter: {
        enabled: true,
        rules: {
          recommended: true,
          correctness: {
            noUnusedVariables: "error",
            noUnusedImports: "error",
          },
          style: {
            useConst: "error",
            useTemplate: "error",
          },
          suspicious: {
            noExplicitAny: "error",
            noConsole: "error",
          },
        },
      },
      formatter: {
        enabled: true,
        indentStyle: "space",
        indentWidth,
        lineWidth,
      },
      javascript: {
        formatter: {
          quoteStyle: "double",
          trailingCommas: "es5",
        },
      },
    },
    null,
    2
  );
}

export const biomeGenerator: ConfigGenerator = {
  id: "biome",
  configFile: "biome.jsonc",
  generate(config: ResolvedConfig): string {
    return withJsoncHashHeader(renderBiomeJson(config));
  },
};
