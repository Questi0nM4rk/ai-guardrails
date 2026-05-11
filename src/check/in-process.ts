import type { HookEvent } from "@questi0nm4rk/hook-kit";
import { evaluate } from "@questi0nm4rk/hook-kit";
import { buildAllModules, loadHookConfig } from "@/check/ruleset";

export type CheckDecision = "allow" | "ask" | "deny";

export type CheckResult =
  | { decision: "allow" }
  | { decision: "ask"; reason: string }
  | { decision: "deny"; reason: string };

export type ToolEvent =
  | { type: "bash"; command: string }
  | { type: "write"; path: string }
  | { type: "read"; path: string };

const PRETOOLUSE = "PreToolUse" as const;

function synthesizeEvent(event: ToolEvent, sessionId: string): HookEvent {
  const base = {
    eventName: PRETOOLUSE,
    sessionId,
    cwd: process.cwd(),
    transcriptPath: "",
    raw: {},
  };
  if (event.type === "bash") {
    return { ...base, toolName: "Bash", toolInput: { command: event.command } };
  }
  return {
    ...base,
    toolName: event.type === "write" ? "Write" : "Read",
    toolInput: { file_path: event.path },
  };
}

/** In-process Bash command evaluation for BDD steps and tests. */
export async function isDangerous(command: string): Promise<CheckResult | null> {
  const result = await evaluateInProcess({ type: "bash", command });
  return result.decision === "allow" ? null : result;
}

/** Generic in-process evaluation — used by BDD step files. */
export async function evaluateInProcess(event: ToolEvent): Promise<CheckResult> {
  const modules = buildAllModules(loadHookConfig());
  const decision = await evaluate(synthesizeEvent(event, "ag-in-process"), modules);
  if (decision === null) return { decision: "allow" };
  if (decision.kind === "deny") return { decision: "deny", reason: decision.reason };
  if (decision.kind === "escalate") return { decision: "ask", reason: decision.reason };
  return { decision: "allow" };
}

export { synthesizeEvent };
