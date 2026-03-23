import { dirname, join } from "node:path";
import type { FileManager } from "@/infra/file-manager";
import { HASH_PREFIX, JSONC_HASH_PREFIX, MD_HASH_PREFIX } from "@/utils/hash";

/**
 * Returns true if the given file content starts with a hash header
 * written by ai-guardrails.
 */
function hasOurHashHeader(content: string): boolean {
  const nlIdx = content.indexOf("\n");
  const firstLine = nlIdx === -1 ? content : content.slice(0, nlIdx);
  return (
    firstLine.startsWith(HASH_PREFIX) ||
    firstLine.startsWith(JSONC_HASH_PREFIX) ||
    firstLine.startsWith(MD_HASH_PREFIX)
  );
}

export type WriteFileResult =
  | { status: "written" }
  | { status: "skipped"; reason: string }
  | { status: "error"; message: string };

/**
 * Write a generated config file respecting conflict rules:
 * - If the file doesn't exist, write it.
 * - If it exists with our hash header, write it (we own it — merge strategy is
 *   handled upstream by the generator).
 * - If it exists without our hash header and force=true, overwrite it.
 * - If it exists without our hash header and force=false, skip with warning.
 */
export async function writeConfigFile(
  projectDir: string,
  configFile: string,
  content: string,
  force: boolean,
  fileManager: FileManager
): Promise<WriteFileResult> {
  const dest = join(projectDir, configFile);

  const exists = await fileManager.exists(dest);
  if (exists) {
    let existing = "";
    try {
      existing = await fileManager.readText(dest);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { status: "error", message: `Failed to read ${configFile}: ${message}` };
    }

    if (!hasOurHashHeader(existing)) {
      if (!force) {
        return {
          status: "skipped",
          reason: `${configFile} exists and is not managed by ai-guardrails — use --force to overwrite`,
        };
      }
      // force=true: overwrite user file
    }
    // Our file: overwrite (already regenerated with merge strategy upstream)
  }

  try {
    await fileManager.mkdir(dirname(dest), { parents: true });
    await fileManager.writeText(dest, content);
    return { status: "written" };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { status: "error", message: `Failed to write ${configFile}: ${message}` };
  }
}
