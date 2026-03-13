import { buildContext } from "@/commands/context";
import { checkPipeline } from "@/pipelines/check";

export async function runCheck(
  projectDir: string,
  flags: Record<string, unknown>
): Promise<void> {
  const ctx = buildContext(projectDir, flags);
  const result = await checkPipeline.run(ctx);
  if (result.status === "error") {
    // Exit 1 = issues found, exit 2 = config/tool error
    const issueCount = result.issueCount ?? 0;
    if (issueCount === 0) {
      process.stderr.write(`Error: ${result.message ?? "unknown error"}\n`);
      process.exit(2);
    }
    process.exit(1);
  }
}
