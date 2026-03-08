import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";

function renderBiomeJson(config: ResolvedConfig): string {
    const lineWidth = config.values.line_length ?? 100;
    const indentWidth = config.values.indent_width ?? 2;
    return JSON.stringify(
        {
            $schema: "https://biomejs.dev/schemas/2.3.15/schema.json",
            assist: { actions: { source: { organizeImports: "on" } } },
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
                        noConsole: "warn",
                        noVar: "error",
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
    configFile: "biome.json",
    generate(config: ResolvedConfig): string {
        return renderBiomeJson(config);
    },
};
