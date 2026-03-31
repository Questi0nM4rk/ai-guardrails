import { join } from "node:path";
import type { FileManager } from "@/infra/file-manager";

/**
 * Parse GitHub workflow files and extract job names for status check contexts.
 *
 * For each job, returns the `name:` value if present, otherwise the job key.
 * These are the exact strings GitHub registers as required status check contexts.
 */
export async function parseWorkflowJobNames(
  projectDir: string,
  fileManager: FileManager
): Promise<readonly string[]> {
  const [ymlFiles, yamlFiles] = await Promise.all([
    fileManager.glob(".github/workflows/*.yml", projectDir),
    fileManager.glob(".github/workflows/*.yaml", projectDir),
  ]);
  const workflowFiles = [...ymlFiles, ...yamlFiles];

  const jobNames: string[] = [];

  for (const file of workflowFiles) {
    const fullPath = join(projectDir, file);
    let content: string;
    try {
      content = await fileManager.readText(fullPath);
    } catch {
      continue;
    }

    jobNames.push(...extractJobNames(content));
  }

  return jobNames;
}

/**
 * Extract job display names from a workflow YAML string.
 * For each job under `jobs:`, uses the `name:` field if present, otherwise the job key.
 */
function extractJobNames(content: string): string[] {
  const lines = content.split("\n");
  const results: string[] = [];
  let currentJobKey: string | undefined;
  let currentJobName: string | undefined;
  let inJobs = false;

  for (const line of lines) {
    // Detect "jobs:" section
    if (/^jobs:\s*$/.test(line)) {
      inJobs = true;
      continue;
    }

    if (!inJobs) continue;

    // A line at indent 0 that isn't blank ends the jobs section
    if (/^\S/.test(line) && line.trim().length > 0) {
      // Flush last job
      if (currentJobKey !== undefined) {
        results.push(currentJobName ?? currentJobKey);
      }
      break;
    }

    // Job key at exactly 2 spaces indent
    const keyMatch = /^ {2}(\w[\w-]*):\s*$/.exec(line);
    if (keyMatch?.[1] !== undefined) {
      // Flush previous job
      if (currentJobKey !== undefined) {
        results.push(currentJobName ?? currentJobKey);
      }
      currentJobKey = keyMatch[1];
      currentJobName = undefined;
      continue;
    }

    // Job name at exactly 4 spaces indent
    const nameMatch = /^ {4}name:\s*["']?([^"'\n]+?)["']?\s*$/.exec(line);
    if (nameMatch?.[1] !== undefined && currentJobKey !== undefined) {
      currentJobName = nameMatch[1].trim();
    }
  }

  // Flush last job
  if (currentJobKey !== undefined) {
    results.push(currentJobName ?? currentJobKey);
  }

  return results;
}
