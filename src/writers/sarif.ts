import type { LintIssue } from "@/models/lint-issue";

interface SarifLocation {
  physicalLocation: {
    artifactLocation: { uri: string };
    region: { startLine: number; startColumn: number };
  };
}

interface SarifResult {
  ruleId: string;
  level: "error" | "warning" | "note";
  message: { text: string };
  locations: SarifLocation[];
}

interface SarifRun {
  tool: { driver: { name: string; version: string; rules: unknown[] } };
  results: SarifResult[];
}

interface SarifLog {
  version: "2.1.0";
  $schema: string;
  runs: SarifRun[];
}

function severityToLevel(severity: LintIssue["severity"]): SarifResult["level"] {
  return severity === "error" ? "error" : "warning";
}

/**
 * Convert LintIssue[] to SARIF 2.1.0 format.
 */
export function issuesToSarif(issues: LintIssue[]): SarifLog {
  const results: SarifResult[] = issues.map((issue) => ({
    ruleId: issue.rule,
    level: severityToLevel(issue.severity),
    message: { text: issue.message },
    locations: [
      {
        physicalLocation: {
          artifactLocation: { uri: issue.file },
          region: { startLine: issue.line, startColumn: issue.col },
        },
      },
    ],
  }));

  const run: SarifRun = {
    tool: {
      driver: {
        name: "ai-guardrails",
        version: "3.0.0",
        rules: [],
      },
    },
    results,
  };

  return {
    version: "2.1.0",
    $schema:
      "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
    runs: [run],
  };
}
