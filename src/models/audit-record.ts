/**
 * One line in .ai-guardrails/audit.jsonl.
 * Append-only log of every check run.
 */
export interface AuditRecord {
    readonly timestamp: string; // ISO 8601
    readonly command: string; // "check", "generate", "snapshot"
    readonly projectDir: string;
    readonly durationMs: number;
    readonly issueCount: number;
    readonly newIssueCount: number;
    readonly exitCode: number;
}
