/**
 * Patterns that the dangerous-cmd hook and claude-settings generator
 * both use to block destructive operations.
 */
export const DANGEROUS_REGEX_PATTERNS: RegExp[] = [
    // rm with both -r and -f in any order:
    // combined short flags (-rf/-fr), split short flags (-r -f), or long GNU flags
    /rm\s+(?:-[a-z]*[rf][a-z]*[rf][a-z]*|-[a-z]*r[a-z]*\s+-[a-z]*f|-[a-z]*f[a-z]*\s+-[a-z]*r|--recursive\s+--force|--force\s+--recursive)\s+(?:[^/\s]*\/?\s*$|\/)/,
    /git\s+push\s+.*(?:--force(?!-with-lease)|-f\b)/,
    /git\s+reset\s+--hard/,
    // require space after -- to avoid false positive on --ours/--theirs
    /git\s+checkout\s+--\s/,
    /git\s+restore\s+--\s/,
    // match both -f (short) and --force (long)
    /git\s+clean\s+(?:-[a-z]*f|--force)/,
    // match --no-verify and -n short alias (and combined like -nm/-an);
    // (?<=\s) ensures the flag starts after whitespace, not inside a quoted message
    /git\s+commit\s+.*(?:--no-verify|(?<=\s)-[a-z]*n[a-z]*(?:\s|$))/,
    // force-delete branch: -D (shorthand), long forms, or mixed -d/--delete with --force
    /git\s+branch\s+(?:-[a-z]*D|--delete\s+--force|--force\s+--delete|-d\s+--force|--force\s+-d)/,
];

/**
 * Claude settings permissions.deny glob patterns used in .claude/settings.json
 * to block dangerous bash commands at the Claude tool-use layer.
 * These cover overlapping but distinct operations from DANGEROUS_REGEX_PATTERNS,
 * which operates at hook runtime.
 */
export const DANGEROUS_DENY_GLOBS: string[] = [
    "Bash(git push --force)",
    "Bash(git push --force *)",
    "Bash(git push -f *)",
    "Bash(git reset --hard*)",
    "Bash(git checkout -- *)",
    "Bash(git restore -- *)",
    "Bash(git clean -f*)",
    "Bash(git clean --force*)",
    "Bash(git commit --no-verify*)",
    "Bash(git commit -n *)",
    "Bash(git branch -D *)",
    "Bash(rm -rf *)",
    "Bash(rm -fr *)",
    "Bash(sudo rm -rf*)",
    "Bash(sudo rm -fr*)",
    "Bash(chmod -R 777*)",
    "Bash(curl * | bash)",
    "Bash(curl * | sh)",
    "Bash(wget * | bash)",
    "Bash(wget * | sh)",
    "Bash(eval $(*))",
    "Bash(python -c*import os*system*)",
];
