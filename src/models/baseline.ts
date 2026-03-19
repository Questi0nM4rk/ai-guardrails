import { join } from "node:path";
import { z } from "zod";

import { BASELINE_PATH } from "@/models/paths";

/**
 * Zod schema for baseline entries. Single source of truth for the type.
 * Stored in .ai-guardrails/baseline.json as an array.
 */
export const BaselineEntrySchema = z.object({
  fingerprint: z.string(),
  rule: z.string(),
  linter: z.string(),
  file: z.string(),
  line: z.number(),
  message: z.string(),
  capturedAt: z.string(),
});

export type BaselineEntry = z.infer<typeof BaselineEntrySchema>;

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
  fileManager: { readText(path: string): Promise<string> }
): Promise<ReadonlyMap<string, BaselineEntry> | null> {
  try {
    const text = await fileManager.readText(join(projectDir, BASELINE_PATH));
    const parsed: unknown = JSON.parse(text);
    const entries = z.array(BaselineEntrySchema).parse(parsed);
    return loadBaseline(entries);
  } catch {
    return null;
  }
}
