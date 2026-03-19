import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import { withJsoncHashHeader } from "@/utils/hash";

function renderBiomeJson(config: ResolvedConfig): string {
  const lineWidth = config.values.line_length ?? 100;
  const indentWidth = config.values.indent_width ?? 2;

  const biomeVersion =
    typeof config.values.biome_version === "string"
      ? config.values.biome_version
      : undefined;
  const schemaSection =
    biomeVersion !== undefined
      ? { $schema: `https://biomejs.dev/schemas/${biomeVersion}/schema.json` }
      : {};

  // Biome v2.4.x uses files.includes with negated globs for exclusions
  const filesSection =
    config.ignorePaths.length > 0
      ? { files: { includes: ["**", ...config.ignorePaths.map((p) => `!${p}`)] } }
      : {};

  return JSON.stringify(
    {
      ...schemaSection,
      ...filesSection,
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
            noConsole: config.noConsoleLevel,
            useBiomeIgnoreFolder: "off",
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
  languages: ["typescript"],
  generate(config: ResolvedConfig): string {
    return withJsoncHashHeader(renderBiomeJson(config));
  },
};
