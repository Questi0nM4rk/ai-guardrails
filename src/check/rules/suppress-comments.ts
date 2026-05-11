import type { Rule } from "@questi0nm4rk/hook-kit";
import { content } from "@questi0nm4rk/hook-kit";
import { scanFile } from "@/hooks/suppress-comments";

const SCANNED_EXT = /\.(py|ts|tsx|js|jsx|rs|go|cs|lua|sh|bash|zsh|ksh|c|cpp|cc|h|hpp)$/;

const PREVIEW_LIMIT = 5;

export function suppressCommentsRule(): Rule {
  return content()
    .matchPath(SCANNED_EXT)
    .validate((filePath, body) => {
      const findings = scanFile(filePath, body);
      if (findings.length === 0) return null;
      const summary = findings
        .slice(0, PREVIEW_LIMIT)
        .map((f) => `  L${f.line}: ${f.pattern}`)
        .join("\n");
      const more =
        findings.length > PREVIEW_LIMIT
          ? `\n  …and ${findings.length - PREVIEW_LIMIT} more`
          : "";
      return {
        kind: "escalate",
        reason:
          `unjustified linter suppression(s) added to ${filePath}:\n${summary}${more}\n\n` +
          `If intentional, add an inline justification:\n` +
          `  # ai-guardrails-allow: <rule> "<reason>"`,
        label: "[suppress-comments]",
      };
    });
}
