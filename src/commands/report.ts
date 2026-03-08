import { join } from "node:path";
import { buildContext } from "@/commands/context";
import type { AuditRecord } from "@/models/audit-record";
import { AUDIT_PATH } from "@/models/paths";

function formatRecord(r: AuditRecord): string {
    const date = r.timestamp.slice(0, 16).replace("T", " ");
    const status = r.exitCode === 0 ? "ok   " : "error";
    return `  ${date}  ${status}  ${r.newIssueCount} new,  ${r.issueCount} total`;
}

export async function runReport(
    projectDir: string,
    flags: Record<string, unknown>
): Promise<void> {
    const ctx = buildContext(projectDir, flags);
    const { fileManager, console: cons } = ctx;

    const last = typeof flags.last === "number" ? flags.last : 10;

    let text: string;
    try {
        text = await fileManager.readText(join(projectDir, AUDIT_PATH));
    } catch {
        cons.info("No audit log found. Run ai-guardrails check first.");
        return;
    }

    const records: AuditRecord[] = text
        .split("\n")
        .filter((l) => l.trim().length > 0)
        .map((l) => JSON.parse(l) as AuditRecord);

    const recent = records.slice(-last);
    if (recent.length === 0) {
        cons.info("No check runs recorded.");
        return;
    }

    cons.info("Recent check history:");
    for (const r of recent) {
        cons.info(formatRecord(r));
    }
}
