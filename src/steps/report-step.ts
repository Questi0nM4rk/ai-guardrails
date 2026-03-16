import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import type { LintIssue } from "@/models/lint-issue";
import type { StepResult } from "@/models/step-result";
import { ok } from "@/models/step-result";
import { issuesToSarif } from "@/writers/sarif";
import { formatIssues } from "@/writers/text";

export type ReportFormat = "text" | "sarif";

export async function reportStep(
  issues: LintIssue[],
  format: ReportFormat,
  console: Console,
  fileManager: FileManager,
  sarifOutputPath?: string
): Promise<StepResult> {
  if (format === "sarif") {
    const sarifJson = JSON.stringify(issuesToSarif(issues), null, 2);
    if (sarifOutputPath) {
      await fileManager.writeText(sarifOutputPath, sarifJson);
    } else {
      console.info(sarifJson);
    }
  }

  if (format === "text") {
    const text = formatIssues(issues);
    if (text) console.error(text);
  }

  return ok(`Reported ${issues.length} issue(s) in ${format} format`);
}
