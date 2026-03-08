import { join } from "node:path";
import { z } from "zod";
import { buildContext } from "@/commands/context";
import type { AuditRecord } from "@/models/audit-record";
import { AUDIT_PATH } from "@/models/paths";

const auditRecordSchema = z.object({
    timestamp: z.string(),
    command: z.string(),
    projectDir: z.string(),
    durationMs: z.number(),
    issueCount: z.number(),
    newIssueCount: z.number(),
    exitCode: z.number(),
});

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

    const records: AuditRecord[] = [];
    for (const l of text.split("\n")) {
        const trimmed = l.trim();
        if (!trimmed) continue;
        try {
            const parsed = auditRecordSchema.parse(JSON.parse(trimmed));
            records.push(parsed);
        } catch {
            // skip malformed lines
        }
    }

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
