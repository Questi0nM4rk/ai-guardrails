import { join, resolve } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { safeParseJson } from "@/utils/parse";

const BIOME_LINTER_ID = "biome";
const BIOME_RULE_PREFIX = "biome/";

// rdjson severity values from biome
const SEVERITY_ERROR = "ERROR";

interface RdjsonRange {
    start: { line: number; character: number };
    end: { line: number; character: number };
}

interface RdjsonDiagnostic {
    location: {
        path: { text: string };
        range: RdjsonRange;
    };
    severity: string;
    code: { value: string };
    message: unknown; // may be string or object with content field
}

interface RdjsonOutput {
    diagnostics: RdjsonDiagnostic[];
}

function extractMessage(message: unknown): string {
    if (typeof message === "string") {
        return message;
    }
    if (
        typeof message === "object" &&
        message !== null &&
        "content" in message &&
        typeof (message as { content: unknown }).content === "string"
    ) {
        return (message as { content: string }).content;
    }
    return String(message);
}

function isRdjsonOutput(value: unknown): value is RdjsonOutput {
    return (
        typeof value === "object" &&
        value !== null &&
        "diagnostics" in value &&
        Array.isArray((value as RdjsonOutput).diagnostics)
    );
}

export function parseBiomeRdjsonOutput(
    stdout: string,
    projectDir: string
): LintIssue[] {
    const parsed = safeParseJson(stdout);
    if (parsed === null) return [];

    if (!isRdjsonOutput(parsed)) {
        return [];
    }

    return parsed.diagnostics.map((diag) => {
        const filePath = resolve(projectDir, diag.location.path.text);
        const line = diag.location.range.start.line + 1;
        const col = diag.location.range.start.character + 1;
        const rule = BIOME_RULE_PREFIX + diag.code.value;
        const message = extractMessage(diag.message);
        const severity: "error" | "warning" =
            diag.severity === SEVERITY_ERROR ? "error" : "warning";
        const fingerprint = computeFingerprint({
            rule,
            file: filePath,
            lineContent: message,
            contextBefore: [],
            contextAfter: [],
        });
        return {
            rule,
            linter: BIOME_LINTER_ID,
            file: filePath,
            line,
            col,
            message,
            severity,
            fingerprint,
        };
    });
}

// Returns the biome executable path to use for the given project directory.
// Prefers local node_modules/.bin/biome so compiled binaries work correctly.
// Falls back to "biome" (global). Returns null when neither is available.
async function resolveBiomePath(
    projectDir: string,
    commandRunner: CommandRunner
): Promise<string | null> {
    const localBiome = join(projectDir, "node_modules", ".bin", "biome");
    const localResult = await commandRunner.run([localBiome, "--version"], {
        cwd: projectDir,
    });
    if (localResult.exitCode === 0) return localBiome;
    const globalResult = await commandRunner.run(["biome", "--version"]);
    if (globalResult.exitCode === 0) return "biome";
    return null;
}

export const biomeRunner: LinterRunner = {
    id: BIOME_LINTER_ID,
    name: "Biome",
    configFile: "biome.json",
    installHint: {
        description: "TypeScript/JS linter and formatter",
        npm: "npm install -D @biomejs/biome",
    },

    async isAvailable(
        commandRunner: CommandRunner,
        projectDir?: string
    ): Promise<boolean> {
        if (projectDir !== undefined) {
            const cmd = await resolveBiomePath(projectDir, commandRunner);
            return cmd !== null;
        }
        const result = await commandRunner.run(["biome", "--version"]);
        return result.exitCode === 0;
    },

    async run({ projectDir, commandRunner }: RunOptions): Promise<LintIssue[]> {
        const cmd = (await resolveBiomePath(projectDir, commandRunner)) ?? "biome";
        const result = await commandRunner.run(
            [cmd, "ci", "--reporter=rdjson", projectDir],
            {
                cwd: projectDir,
            }
        );
        // biome exits non-zero when issues are found — parse stdout regardless
        return parseBiomeRdjsonOutput(result.stdout, projectDir);
    },
};
