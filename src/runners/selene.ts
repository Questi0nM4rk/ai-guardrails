import { resolve } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { safeParseJson } from "@/utils/parse";

const SELENE_LINTER_ID = "selene";
const SELENE_RULE_PREFIX = "selene/";

/** Single entry in selene's Json2 output array */
interface SeleneEntry {
    filename: string;
    primary_label: string;
    code: string;
    severity: string;
    start_line: number;
    start_column: number;
}

function isSeleneEntry(value: unknown): value is SeleneEntry {
    return (
        typeof value === "object" &&
        value !== null &&
        "filename" in value &&
        "primary_label" in value &&
        "code" in value &&
        "severity" in value &&
        "start_line" in value &&
        "start_column" in value
    );
}

/**
 * Parse selene --display-style=Json2 stdout into LintIssue[].
 * Returns [] on malformed or empty input.
 */
export function parseSeleneOutput(stdout: string, projectDir: string): LintIssue[] {
    const parsed = safeParseJson(stdout);
    if (!Array.isArray(parsed)) return [];

    const issues: LintIssue[] = [];
    for (const entry of parsed) {
        if (!isSeleneEntry(entry)) continue;
        const rule = SELENE_RULE_PREFIX + entry.code;
        const file = resolve(projectDir, entry.filename);
        const severity: "error" | "warning" =
            entry.severity === "Error" ? "error" : "warning";
        const fingerprint = computeFingerprint({
            rule,
            file,
            lineContent: entry.primary_label,
            contextBefore: [],
            contextAfter: [],
        });
        issues.push({
            rule,
            linter: SELENE_LINTER_ID,
            file,
            line: entry.start_line,
            col: entry.start_column,
            message: entry.primary_label,
            severity,
            fingerprint,
        });
    }
    return issues;
}

export const seleneRunner: LinterRunner = {
    id: SELENE_LINTER_ID,
    name: "Selene",
    configFile: "selene.toml",
    installHint: {
        description: "Lua linter",
        cargo: "cargo install selene",
        brew: "brew install selene",
    },

    async isAvailable(commandRunner: CommandRunner): Promise<boolean> {
        const result = await commandRunner.run(["selene", "--version"]);
        return result.exitCode === 0;
    },

    async run({
        projectDir,
        commandRunner,
        fileManager,
    }: RunOptions): Promise<LintIssue[]> {
        const luaFiles = await fileManager.glob("**/*.lua", projectDir);
        if (luaFiles.length === 0) return [];

        const result = await commandRunner.run(
            ["selene", "--display-style=Json2", projectDir],
            {
                cwd: projectDir,
            }
        );
        // selene exits non-zero when issues are found — parse stdout regardless
        return parseSeleneOutput(result.stdout, projectDir);
    },
};
