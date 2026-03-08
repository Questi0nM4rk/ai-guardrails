import { dirname, join } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { generateLefthookConfig, lefthookGenerator } from "@/generators/lefthook";
import { ALL_GENERATORS } from "@/generators/registry";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";

async function runGenerator(
    projectDir: string,
    config: ResolvedConfig,
    fileManager: FileManager,
    generator: (typeof ALL_GENERATORS)[number]
): Promise<{ file: string } | { error: string }> {
    try {
        const content = generator.generate(config);
        const dest = join(projectDir, generator.configFile);
        await fileManager.mkdir(dirname(dest), { parents: true });
        await fileManager.writeText(dest, content);
        return { file: generator.configFile };
    } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return { error: `${generator.id}: ${message}` };
    }
}

export async function generateConfigsStep(
    projectDir: string,
    languages: readonly LanguagePlugin[],
    config: ResolvedConfig,
    fileManager: FileManager
): Promise<StepResult> {
    // Run all generators except lefthook (which requires language awareness).
    const otherGenerators = ALL_GENERATORS.filter((g) => g.id !== lefthookGenerator.id);
    const results = await Promise.all([
        ...otherGenerators.map((g) => runGenerator(projectDir, config, fileManager, g)),
        (async (): Promise<{ file: string } | { error: string }> => {
            try {
                const content = generateLefthookConfig(config, languages);
                const dest = join(projectDir, lefthookGenerator.configFile);
                await fileManager.mkdir(dirname(dest), { parents: true });
                await fileManager.writeText(dest, content);
                return { file: lefthookGenerator.configFile };
            } catch (err) {
                const message = err instanceof Error ? err.message : String(err);
                return { error: `${lefthookGenerator.id}: ${message}` };
            }
        })(),
    ]);

    const written: string[] = [];
    const errors: string[] = [];
    for (const r of results) {
        if ("file" in r) written.push(r.file);
        else errors.push(r.error);
    }

    if (errors.length > 0) {
        return error(`Config generation failed: ${errors.join(", ")}`);
    }

    return ok(`Generated ${written.length} config file(s): ${written.join(", ")}`);
}
