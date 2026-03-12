import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import type { FileManager } from "@/infra/file-manager";
import { withMarkdownHashHeader } from "@/utils/hash";

/** AI tool detection results */
export interface DetectedAgentTools {
    claude: boolean;
    cursor: boolean;
    windsurf: boolean;
    copilot: boolean;
    cline: boolean;
    aider: boolean;
}

/** Detect which AI agent tools are configured in the project */
export async function detectAgentTools(
    projectDir: string,
    fileManager: FileManager
): Promise<DetectedAgentTools> {
    // Run all existence checks and the cursor-rules glob in parallel
    const [
        claudeSettings,
        claudeMd,
        cursorRules,
        cursorDir,
        windsurf,
        copilot,
        cline,
        aider,
        cursorRulesFiles,
    ] = await Promise.all([
        fileManager.exists(`${projectDir}/.claude/settings.json`),
        fileManager.exists(`${projectDir}/.claude/CLAUDE.md`),
        fileManager.exists(`${projectDir}/.cursorrules`),
        fileManager.exists(`${projectDir}/.cursor/rules`),
        fileManager.exists(`${projectDir}/.windsurfrules`),
        fileManager.exists(`${projectDir}/.github/copilot-instructions.md`),
        fileManager.exists(`${projectDir}/.clinerules`),
        fileManager.exists(`${projectDir}/.aider.conf.yml`),
        fileManager.glob("**/.cursor/rules/**", projectDir),
    ]);

    return {
        claude: claudeSettings || claudeMd,
        cursor: cursorRules || cursorDir || cursorRulesFiles.length > 0,
        windsurf,
        copilot,
        cline,
        aider,
    };
}

const BASE_RULES = `# AI Agent Rules

## Core Principles

- Never push directly to main — always open a PR
- Never commit secrets, credentials, or .env files
- Run tests before committing: all tests must pass
- Fix ALL review findings including nitpicks
- Never batch-resolve review threads without reading each one

## Git Workflow

- Conventional commit messages: feat:, fix:, refactor:, chore:, test:, docs:
- Create feature branches: git checkout -b feat/<name>
- Keep commits focused — one logical change per commit

## Code Quality

- No any — use unknown + type narrowing at boundaries
- No non-null assertions (!) — handle undefined explicitly
- No commented-out code — delete it or open an issue
- No TODO without an issue reference

## Security

- Never log secrets, tokens, or passwords
- Never eval() user input
- Never trust user-provided paths without sanitization
`;

const CLAUDE_ADDITIONS = `
## Claude Code Specific

- Read CLAUDE.md at the start of each session
- Use PreToolUse hooks — they protect configs and catch dangerous commands
- Never disable the hook system to bypass restrictions
- The deny list in .claude/settings.json exists for safety — don't circumvent it
`;

const CURSOR_ADDITIONS = `
## Cursor Specific

- Follow the project's existing code style — don't reformat arbitrarily
- Check existing tests before adding new ones — avoid duplication
- Prefer editing existing files over creating new ones
`;

const WINDSURF_ADDITIONS = `
## Windsurf Specific

- Follow the project's existing code style
- Check for existing utilities before implementing new ones
- Run the test suite before marking a task complete
`;

const COPILOT_ADDITIONS = `
## GitHub Copilot Specific

- This project uses strict linting — suggestions must pass lint and typecheck
- Follow conventional commit format for all commit messages
- Check existing patterns in the codebase before suggesting new abstractions
`;

const CLINE_ADDITIONS = `
## Cline Specific

- Always read existing code before making changes
- Prefer minimal diffs — change only what is necessary
- Verify tests pass after each change
`;

const AIDER_ADDITIONS = `
## Aider Specific

- Use conventional commit messages (aider formats these automatically)
- Keep changes focused — avoid unrelated edits in the same session
- Run the test suite to verify changes before ending the session
`;

/** Symlink targets for each AI tool's rules file */
export const AGENT_SYMLINKS: Readonly<Record<string, string>> = {
    cursor: ".cursorrules",
    windsurf: ".windsurfrules",
    copilot: ".github/copilot-instructions.md",
    cline: ".clinerules",
} as const;

const TOOL_ADDITIONS: Partial<Record<keyof DetectedAgentTools, string>> = {
    claude: CLAUDE_ADDITIONS,
    cursor: CURSOR_ADDITIONS,
    windsurf: WINDSURF_ADDITIONS,
    copilot: COPILOT_ADDITIONS,
    cline: CLINE_ADDITIONS,
    aider: AIDER_ADDITIONS,
};

/** Build the combined rules content for a specific agent tool */
export function buildAgentRules(tool: keyof DetectedAgentTools): string {
    return BASE_RULES + (TOOL_ADDITIONS[tool] ?? "");
}

export const agentRulesGenerator: ConfigGenerator = {
    id: "agent-rules",
    configFile: ".ai-guardrails/agent-rules/base.md",
    generate(_config: ResolvedConfig): string {
        return withMarkdownHashHeader(BASE_RULES);
    },
};
