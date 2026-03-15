import type { CheckResult } from "@/check/types";

export function toHookOutput(result: CheckResult, label: string): never {
  if (result.decision === "allow") {
    process.exit(0);
  }
  if (result.decision === "ask") {
    process.stdout.write(
      JSON.stringify({
        permissionDecision: "ask",
        reason: `[${label}] ${result.reason}`,
      })
    );
    process.exit(0);
  }
  process.stderr.write(`[${label}] ${result.reason}\n`);
  process.exit(2);
}
