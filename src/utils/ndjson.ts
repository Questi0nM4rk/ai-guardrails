/**
 * Parse NDJSON (newline-delimited JSON) — one JSON object per line.
 * Skips blank lines and lines that fail to parse.
 */
export function parseNdjson(text: string): unknown[] {
    const results: unknown[] = [];
    for (const line of text.split("\n")) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
            results.push(JSON.parse(trimmed));
        } catch {
            // Skip malformed lines
        }
    }
    return results;
}
