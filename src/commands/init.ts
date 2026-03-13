import { buildContext } from "@/commands/context";
import { initPipeline } from "@/pipelines/init";

export async function runInit(
  projectDir: string,
  flags: Record<string, unknown>
): Promise<void> {
  const ctx = buildContext(projectDir, flags);
  const result = await initPipeline.run(ctx);
  if (result.status === "error") {
    process.stderr.write(`Error: ${result.message ?? "init failed"}\n`);
    process.exit(2);
  }
}
