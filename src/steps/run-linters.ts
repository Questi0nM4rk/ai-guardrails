import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import type { LintIssue } from "@/models/lint-issue";

/**
 * Run all linter runners for the given language plugins and collect their issues.
 * Runners that report themselves unavailable are skipped.
 */
export async function runLinterCollection(
    projectDir: string,
    languages: readonly LanguagePlugin[],
    config: ResolvedConfig,
    commandRunner: CommandRunner,
    fileManager: FileManager
): Promise<LintIssue[]> {
    const opts = { projectDir, config, commandRunner, fileManager };
    const results = await Promise.all(
        languages.flatMap((plugin) =>
            plugin.runners().map(async (runner) => {
                const available = await runner.isAvailable(commandRunner, projectDir);
                if (!available) return [] as LintIssue[];
                return runner.run(opts);
            })
        )
    );
    return results.flat();
}
