import { extname } from "node:path";
import { parseAllowComments } from "@/hooks/allow-comment";

const SUPPRESSION_PATTERNS: Record<string, RegExp[]> = {
  python: [/# noqa/, /# type:\s*ignore/, /# pragma:\s*no cover/, /# pylint:\s*disable/],
  typescript: [
    /\/\/\s*@ts-ignore/,
    /\/\/\s*@ts-nocheck/,
    /eslint-disable/, // ai-guardrails-allow: suppress-comments/eslint-disable "pattern definition — not an active suppression"
    /\/\*\s*tslint:disable/,
    /nosemgrep/, // ai-guardrails-allow: suppress-comments/nosemgrep "pattern definition — not an active suppression"
  ],
  rust: [/#\[allow\(/, /#!\[allow\(/],
  go: [/\/\/nolint/, /\/\/\s*nolint/],
  csharp: [/#pragma warning disable/, /\[SuppressMessage/],
  lua: [/--\s*luacheck:\s*ignore/, /--\s*luacheck:\s*disable/],
  shell: [/# shellcheck disable/],
  cpp: [/\/\/ NOLINT/, /#pragma diagnostic ignored/, /#pragma GCC diagnostic ignored/],
};

const EXT_TO_LANG: Record<string, string> = {
  ".py": "python",
  ".ts": "typescript",
  ".tsx": "typescript",
  ".js": "typescript",
  ".jsx": "typescript",
  ".rs": "rust",
  ".go": "go",
  ".cs": "csharp",
  ".lua": "lua",
  ".sh": "shell",
  ".bash": "shell",
  ".zsh": "shell",
  ".ksh": "shell",
  ".c": "cpp",
  ".cpp": "cpp",
  ".cc": "cpp",
  ".h": "cpp",
  ".hpp": "cpp",
};

const GENERIC_SUPPRESSION =
  /\b(nolint|nocheck|nosemgrep|suppress|pragma\s+ignore|NOLINT)\b/;
const BLOCK_COMMENT = /\/\*(.+?)\*\//;

interface Finding {
  file: string;
  line: number;
  pattern: string;
}

/**
 * Extract the comment portion of a line, ignoring code.
 * Handles //, #, --, and inline block comments.
 * Returns empty string if no comment is found.
 */
export function extractComment(line: string): string {
  const blockMatch = BLOCK_COMMENT.exec(line);
  if (blockMatch) return blockMatch[1] ?? "";

  const slashIdx = line.indexOf("//");
  if (slashIdx !== -1) return line.slice(slashIdx + 2);

  const hashIdx = line.indexOf("#");
  if (hashIdx !== -1) return line.slice(hashIdx + 1);

  const dashIdx = line.indexOf("--");
  if (dashIdx !== -1) return line.slice(dashIdx + 2);

  return "";
}

export function scanFile(filePath: string, content: string): Finding[] {
  const ext = extname(filePath);
  const lang = EXT_TO_LANG[ext];
  if (!lang) return [];

  const patterns = SUPPRESSION_PATTERNS[lang] ?? [];
  const findings: Finding[] = [];
  const lines = content.split("\n");
  const allowedLines = new Set(parseAllowComments(lines).map((c) => c.line));
  const flaggedLines = new Set<number>();

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? "";
    if (allowedLines.has(i + 1)) continue;
    for (const pattern of patterns) {
      if (pattern.test(line)) {
        findings.push({ file: filePath, line: i + 1, pattern: pattern.source });
        flaggedLines.add(i + 1);
        break;
      }
    }
  }

  // Second pass: generic comment-only keyword scanner
  for (let i = 0; i < lines.length; i++) {
    const lineNum = i + 1;
    if (allowedLines.has(lineNum) || flaggedLines.has(lineNum)) continue;
    const comment = extractComment(lines[i] ?? "");
    if (comment !== "" && GENERIC_SUPPRESSION.test(comment)) {
      findings.push({
        file: filePath,
        line: lineNum,
        pattern: "generic-suppression-keyword",
      });
    }
  }

  return findings;
}

async function readFileSafe(path: string): Promise<string | null> {
  try {
    return await Bun.file(path).text();
  } catch {
    return null;
  }
}

export async function runSuppressComments(files: string[]): Promise<never> {
  const results = await Promise.all(
    files.map(async (file) => {
      const content = await readFileSafe(file);
      return content !== null ? scanFile(file, content) : [];
    })
  );
  const allFindings = results.flat();

  if (allFindings.length > 0) {
    for (const f of allFindings) {
      process.stderr.write(
        `${f.file}:${f.line}: suppression comment detected (${f.pattern})\n`
      );
    }
    process.stderr.write(
      'Use "# ai-guardrails-allow: linter/RULE \\"reason\\"" instead of inline suppression.\n'
    );
    process.exit(1);
  }

  process.exit(0);
}
