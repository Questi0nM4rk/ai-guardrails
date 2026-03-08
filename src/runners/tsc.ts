import { join, resolve } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";

const TSC_LINTER_ID = "tsc";
const TSC_RULE_PREFIX = "tsc/";

// Matches lines like: src/foo.ts(10,5): error TS2322: Type 'string' is not assignable...
const TSC_LINE_PATTERN = /^(.+)\((\d+),(\d+)\):\s+(error|warning)\s+(TS\d+):\s+(.+)$/;

interface TscMatch {
    file: string;
    line: number;
    col: number;
    severity: "error" | "warning";
    tsCode: string;
    message: string;
}

function parseTscLine(line: string): TscMatch | null {
    const match = TSC_LINE_PATTERN.exec(line);
    if (!match) return null;
    const [, file, lineStr, colStr, rawSeverity, tsCode, message] = match;
    if (!file || !lineStr || !colStr || !rawSeverity || !tsCode || !message)
        return null;
    return {
        file,
        line: Number.parseInt(lineStr, 10),
        col: Number.parseInt(colStr, 10),
        severity: rawSeverity === "warning" ? "warning" : "error",
        tsCode,
        message,
    };
}

export function parseTscOutput(output: string, projectDir: string): LintIssue[] {
    const issues: LintIssue[] = [];
    for (const line of output.split("\n")) {
        const parsed = parseTscLine(line);
        if (!parsed) continue;
        const filePath = resolve(projectDir, parsed.file);
        const rule = TSC_RULE_PREFIX + parsed.tsCode;
        const fingerprint = computeFingerprint({
            rule,
            file: filePath,
            lineContent: parsed.message,
            contextBefore: [],
            contextAfter: [],
        });
        issues.push({
            rule,
            linter: TSC_LINTER_ID,
            file: filePath,
            line: parsed.line,
            col: parsed.col,
            message: parsed.message,
            severity: parsed.severity,
            fingerprint,
        });
    }
    return issues;
}

// Returns the tsc executable path to use for the given project directory.
// Prefers local node_modules/.bin/tsc so compiled binaries (which don't add
// node_modules/.bin to PATH) still work. Falls back to "tsc" (global) when local
// is absent. Returns null when neither is available.
async function resolveTscPath(
    projectDir: string,
    commandRunner: CommandRunner
): Promise<string | null> {
    const localTsc = join(projectDir, "node_modules", ".bin", "tsc");
    const localResult = await commandRunner.run([localTsc, "--version"], {
        cwd: projectDir,
    });
    if (localResult.exitCode === 0) return localTsc;
    const globalResult = await commandRunner.run(["tsc", "--version"]);
    if (globalResult.exitCode === 0) return "tsc";
    return null;
}

export const tscRunner: LinterRunner = {
    id: TSC_LINTER_ID,
    name: "TypeScript Compiler",
    configFile: null,
    installHint: {
        description: "TypeScript type checker",
        npm: "npm install -D typescript",
    },

    async isAvailable(
        commandRunner: CommandRunner,
        projectDir?: string
    ): Promise<boolean> {
        const tsc = await resolveTscPath(projectDir ?? ".", commandRunner);
        return tsc !== null;
    },

    async run({ projectDir, commandRunner }: RunOptions): Promise<LintIssue[]> {
        const tsc = (await resolveTscPath(projectDir, commandRunner)) ?? "tsc";
        const result = await commandRunner.run([tsc, "--noEmit", "--pretty", "false"], {
            cwd: projectDir,
        });
        // tsc exits non-zero when errors exist — parse stdout+stderr
        const combined = `${result.stdout}\n${result.stderr}`;
        return parseTscOutput(combined, projectDir);
    },
};
