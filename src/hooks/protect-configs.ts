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
    ".claude/settings.json",
    ".github/copilot-instructions.md",
    ".github/workflows/guardrails-check.yml",
];

// Non-redirect write patterns — these don't need file-position anchoring
// because the operation name itself implies a write (tee, sed -i, cp dest, mv dest).
const WRITE_PATTERNS: RegExp[] = [
    /\btee\b/,
    /\bsed\s+-i/,
    /\bawk\b.*>|>\s*\bawk\b/,
    /\bcat\s+.*>/,
    /\bprintf\b.*>/,
    /\becho\b.*>/,
    /\bcp\b/,
    /\bmv\b/,
];

function escapeRegex(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function protectsFile(command: string): string | null {
    for (const managed of MANAGED_FILES) {
        if (!command.includes(managed)) continue;

        // For redirect operators, anchor to the managed file being the write target.
        // Bare />/ matched any > in the command (e.g. reading ruff.toml on the left
        // side of a redirect, or ruff.toml appearing only in a commit message).
        const redirectToManaged = new RegExp(
            String.raw`>>?\s*(?:\S+\/)*${escapeRegex(managed)}\b`
        );
        if (redirectToManaged.test(command)) {
            return `Blocked: attempt to write managed config file: ${managed}`;
        }

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
