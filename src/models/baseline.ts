import { join } from "node:path";
import { z } from "zod";

const BaselineEntrySchema = z.object({
  fingerprint: z.string(),
  rule: z.string(),
  linter: z.string(),
  file: z.string(),
  line: z.number(),
  message: z.string(),
  capturedAt: z.string(),
});

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

/**
 * Load a baseline from a file on disk. Returns null if the file doesn't exist
 * or contains invalid data. Uses Zod for safe parsing at the file boundary.
 */
export async function loadBaselineFromFile(
  projectDir: string,
  baselinePath: string,
  fileManager: { readText(path: string): Promise<string> }
): Promise<ReadonlyMap<string, BaselineEntry> | null> {
  try {
    const text = await fileManager.readText(join(projectDir, baselinePath));
    const parsed: unknown = JSON.parse(text);
    const entries = z.array(BaselineEntrySchema).parse(parsed);
    return loadBaseline(entries);
  } catch {
    return null;
  }
}
