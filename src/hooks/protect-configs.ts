import { allow, deny, readHookInput } from "@/hooks/runner";
import { extractBashCommand } from "@/hooks/types";

export const MANAGED_FILES: readonly string[] = [
    "ruff.toml",
    "mypy.ini",
    "biome.jsonc",
    ".editorconfig",
    ".markdownlint.jsonc",
    ".codespellrc",
    "lefthook.yml",
    ".clang-tidy",
    ".luacheckrc",
    "staticcheck.conf",
    "AGENTS.md",
    ".cursorrules",
    ".windsurfrules",
    ".github/copilot-instructions.md",
    ".github/workflows/guardrails-check.yml",
];

const WRITE_PATTERNS: RegExp[] = [
    />/,
    /\btee\b/,
    /\bsed\s+-i/,
    /\bawk\b.*>|>\s*\bawk\b/,
    /\bcat\s+.*>/,
    /\bprintf\b.*>/,
    /\becho\b.*>/,
    /\bcp\b/,
    /\bmv\b/,
];

export function protectsFile(command: string): string | null {
    for (const managed of MANAGED_FILES) {
        if (!command.includes(managed)) continue;
        for (const pattern of WRITE_PATTERNS) {
            if (pattern.test(command)) {
                return `Blocked: attempt to write managed config file: ${managed}`;
            }
        }
    }
    return null;
}

export async function runProtectConfigs(): Promise<never> {
    const input = await readHookInput();
    const command = extractBashCommand(input.tool_input);
    const reason = protectsFile(command);
    if (reason !== null) {
        deny(`[protect-configs] ${reason}`);
    }
    allow();
}
