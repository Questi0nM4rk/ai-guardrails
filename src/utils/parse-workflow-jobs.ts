import { join } from "node:path";
import type { FileManager } from "@/infra/file-manager";

// Matches a top-level job key under "jobs:" — exactly 2 leading spaces, word chars.
const JOB_KEY_REGEX = /^ {2}(\w[\w-]*):\s*$/gm;
// Matches a "name:" property under a job — exactly 4 leading spaces.
const JOB_NAME_REGEX = /^ {4}name:\s*["']?([^"'\n]+?)["']?\s*$/gm;

/**
 * Parse GitHub workflow files and extract job names for status check contexts.
 *
 * Returns human-readable job names (from `name:` fields) when present,
 * falling back to job keys when no `name:` is set. These are the exact
 * strings GitHub registers as required status check contexts.
 */
export async function parseWorkflowJobNames(
  projectDir: string,
  fileManager: FileManager
): Promise<readonly string[]> {
  const workflowFiles = await fileManager.glob(".github/workflows/*.yml", projectDir);

  const jobNames: string[] = [];

  for (const file of workflowFiles) {
    const fullPath = join(projectDir, file);
    let content: string;
    try {
      content = await fileManager.readText(fullPath);
    } catch {
      continue;
    }

    const keys = extractMatches(JOB_KEY_REGEX, content);
    const names = extractMatches(JOB_NAME_REGEX, content).map((n) => n.trim());

    if (names.length > 0) {
      jobNames.push(...names);
    } else {
      jobNames.push(...keys);
    }
  }

  return jobNames;
}

/** Extract first capture group from all matches of a global regex against content. */
function extractMatches(regex: RegExp, content: string): string[] {
  regex.lastIndex = 0;
  const results: string[] = [];
  const matches = content.matchAll(regex);
  for (const match of matches) {
    if (match[1] !== undefined) results.push(match[1]);
  }
  return results;
}
