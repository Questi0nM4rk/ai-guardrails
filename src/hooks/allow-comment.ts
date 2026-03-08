export interface AllowComment {
    rule: string;
    reason: string;
    line: number; // 1-indexed
}

// Matches: # ... ai-guardrails-allow: RULE "reason"
//          // ... ai-guardrails-allow: RULE "reason"
//          -- ... ai-guardrails-allow: RULE "reason"
const ALLOW_PATTERN =
    /(?:#|\/\/|--)[ \t]*ai-guardrails-allow:[ \t]*([\w/-]+)[ \t]+"([^"]+)"/;

/**
 * Parse all inline allow comments from source lines.
 * Returns one AllowComment per matched line.
 * Lines without a valid allow comment (or without a quoted reason) are skipped.
 */
export function parseAllowComments(sourceLines: string[]): AllowComment[] {
    const results: AllowComment[] = [];

    for (let i = 0; i < sourceLines.length; i++) {
        const line = sourceLines[i];
        if (line === undefined) continue;

        const match = ALLOW_PATTERN.exec(line);
        if (!match) continue;

        const rule = match[1]?.trim();
        const reason = match[2]?.trim();
        if (!rule || !reason) continue;

        results.push({
            rule,
            reason,
            line: i + 1, // 1-indexed
        });
    }

    return results;
}
