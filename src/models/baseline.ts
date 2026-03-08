/**
 * A single entry in the baseline snapshot.
 * Stored in .ai-guardrails/baseline.json as an array.
 */
export interface BaselineEntry {
    readonly fingerprint: string;
    readonly rule: string;
    readonly linter: string;
    readonly file: string; // project-relative path
    readonly line: number;
    readonly message: string;
    readonly capturedAt: string; // ISO 8601
}

/**
 * Comparison result when checking a LintIssue against the baseline.
 */
export type BaselineStatus = "new" | "existing" | "resolved";

/**
 * Load a baseline from parsed JSON (already validated).
 */
export function loadBaseline(
    entries: readonly BaselineEntry[]
): ReadonlyMap<string, BaselineEntry> {
    return new Map(entries.map((e) => [e.fingerprint, e]));
}

/**
 * Determine if a fingerprint is new relative to the baseline.
 */
export function classifyFingerprint(
    fingerprint: string,
    baseline: ReadonlyMap<string, BaselineEntry>
): BaselineStatus {
    return baseline.has(fingerprint) ? "existing" : "new";
}
