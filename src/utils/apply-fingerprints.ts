import { relative } from "node:path";
import type { FileManager } from "@/infra/file-manager";
import type { LintIssue } from "@/models/lint-issue";
import { groupBy } from "@/utils/collections";
import { fingerprintIssue } from "@/utils/fingerprint";

/**
 * Add content-stable fingerprints to raw lint issues by reading actual source lines.
 *
 * Groups issues by absolute file path, reads all files in parallel, then calls
 * fingerprintIssue() with the surrounding source lines. If a file cannot be
 * read (e.g. deleted between lint and fingerprint), empty sourceLines are
 * used — fingerprintIssue handles this gracefully (line content becomes "").
 *
 * @param raw    Issues without fingerprints. `file` must be an absolute path.
 * @param projectDir  Project root — used to derive a portable relative path for fingerprinting.
 * @param fileManager Injected I/O abstraction.
 */
export async function applyFingerprints(
  raw: Omit<LintIssue, "fingerprint">[],
  projectDir: string,
  fileManager: FileManager
): Promise<LintIssue[]> {
  const byFile = groupBy(raw, (i) => i.file);

  // Read all source files in parallel — one I/O operation per unique file.
  const readFile = async (absFile: string): Promise<string[]> => {
    try {
      const text = await fileManager.readText(absFile);
      return text.split("\n");
    } catch {
      return [];
    }
  };

  const absFiles = [...byFile.keys()];
  const sourceLinesPerFile = await Promise.all(absFiles.map(readFile));

  const issues: LintIssue[] = [];
  for (let i = 0; i < absFiles.length; i++) {
    const absFile = absFiles[i];
    const sourceLines = sourceLinesPerFile[i];
    const group = byFile.get(absFile ?? "");
    if (!absFile || !sourceLines || !group) continue;

    const relFile = relative(projectDir, absFile);
    for (const issue of group) {
      const fingerprint = fingerprintIssue({ ...issue, file: relFile }, sourceLines);
      issues.push({ ...issue, fingerprint });
    }
  }
  return issues;
}
