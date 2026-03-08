/**
 * Parse JSON text, returning null on any parse error.
 * Use this instead of try/catch around JSON.parse.
 */
export function safeParseJson(text: string): unknown {
    try {
        return JSON.parse(text);
    } catch {
        return null;
    }
}
