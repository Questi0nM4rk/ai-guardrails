/**
 * Patterns that the dangerous-cmd hook and claude-settings generator
 * both use to block destructive operations.
 */
export const DANGEROUS_REGEX_PATTERNS: RegExp[] = [
    /rm\s+-rf?\s+[^/\s]*\/?\s*$|rm\s+-rf\s+\//,
    /git\s+push\s+.*(?:--force(?!-with-lease)|-f\b)/,
    /git\s+reset\s+--hard/,
    /git\s+checkout\s+--/,
    /git\s+clean\s+-[a-z]*f/,
    /git\s+commit\s+.*--no-verify/,
];

/**
 * Claude settings permissions.deny glob patterns corresponding to DANGEROUS_REGEX_PATTERNS.
 * These are used in .claude/settings.json to block dangerous bash commands.
 */
export const DANGEROUS_DENY_GLOBS: string[] = [
    "Bash(git push*)",
    "Bash(git push --force*)",
    "Bash(rm -rf /*)",
    "Bash(sudo rm -rf*)",
    "Bash(chmod -R 777*)",
    "Bash(curl * | bash)",
    "Bash(wget * | bash)",
    "Bash(eval $(*))",
    "Bash(python -c*import os*system*)",
];
