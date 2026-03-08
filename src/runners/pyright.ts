import { join } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { safeParseJson } from "@/utils/parse";

interface PyrightRange {
    start: { line: number; character: number };
    end: { line: number; character: number };
}

interface PyrightDiagnostic {
    file: string;
    severity: string;
    message: string;
    range: PyrightRange;
    rule?: string;
}

interface PyrightOutput {
    generalDiagnostics: PyrightDiagnostic[];
}

function isPyrightRange(value: unknown): value is PyrightRange {
    if (typeof value !== "object" || value === null) return false;
    const v = value as { start: unknown };
    const start = v.start;
    return (
        typeof start === "object" &&
        start !== null &&
        typeof (start as { line: unknown; character: unknown }).line === "number" &&
        typeof (start as { line: unknown; character: unknown }).character === "number"
    );
}

function isPyrightDiagnostic(value: unknown): value is PyrightDiagnostic {
    if (typeof value !== "object" || value === null) return false;
    const v = value as PyrightDiagnostic & { range: unknown };
    return (
        typeof v.file === "string" &&
        typeof v.severity === "string" &&
        typeof v.message === "string" &&
        isPyrightRange(v.range)
    );
}

function isPyrightOutput(value: unknown): value is PyrightOutput {
    if (typeof value !== "object" || value === null) return false;
    const v = value as { generalDiagnostics: unknown };
    return Array.isArray(v.generalDiagnostics);
}

/**
 * Parse pyright --outputjson output into normalized LintIssue[].
 * Skips information-level diagnostics.
 * Returns [] for empty stdout or invalid JSON.
 */
export function parsePyrightOutput(stdout: string): LintIssue[] {
    if (!stdout.trim()) return [];

    const parsed = safeParseJson(stdout);
    if (parsed === null) return [];

    if (!isPyrightOutput(parsed)) return [];

    const issues: LintIssue[] = [];
    for (const diag of parsed.generalDiagnostics) {
        if (!isPyrightDiagnostic(diag)) continue;
        if (diag.severity === "information") continue;

        const rule = `pyright/${diag.rule ?? "unknown"}`;
        // pyright uses 0-indexed lines and columns; LintIssue is 1-indexed
        const line = diag.range.start.line + 1;
        const col = diag.range.start.character + 1;

        const fingerprint = computeFingerprint({
            rule,
            file: diag.file,
            lineContent: diag.message,
            contextBefore: [],
            contextAfter: [],
        });

        issues.push({
            rule,
            linter: "pyright",
            file: diag.file,
            line,
            col,
            message: diag.message,
            severity: diag.severity === "error" ? "error" : "warning",
            fingerprint,
        });
    }
    return issues;
}

// Returns the pyright executable path to use for the given project directory.
// Prefers local node_modules/.bin/pyright so compiled binaries work correctly.
// Falls back to "pyright" (global). Returns null when neither is available.
async function resolvePyrightPath(
    projectDir: string,
    commandRunner: CommandRunner
): Promise<string | null> {
    const localPyright = join(projectDir, "node_modules", ".bin", "pyright");
    const localResult = await commandRunner.run([localPyright, "--version"], {
        cwd: projectDir,
    });
    if (localResult.exitCode === 0) return localPyright;
    const globalResult = await commandRunner.run(["pyright", "--version"]);
    if (globalResult.exitCode === 0) return "pyright";
    return null;
}

export const pyrightRunner: LinterRunner = {
    id: "pyright",
    name: "Pyright",
    configFile: "pyrightconfig.json",
    installHint: {
        description: "Python type checker",
        npm: "npm install -D pyright",
        pip: "pip install pyright",
    },

    async isAvailable(runner: CommandRunner, projectDir?: string): Promise<boolean> {
        if (projectDir !== undefined) {
            const cmd = await resolvePyrightPath(projectDir, runner);
            return cmd !== null;
        }
        const result = await runner.run(["pyright", "--version"]);
        return result.exitCode === 0;
    },

    async run(opts: RunOptions): Promise<LintIssue[]> {
        const { projectDir, commandRunner } = opts;
        const cmd = (await resolvePyrightPath(projectDir, commandRunner)) ?? "pyright";
        const result = await commandRunner.run([cmd, "--outputjson", projectDir], {
            cwd: projectDir,
        });
        return parsePyrightOutput(result.stdout);
    },
};
