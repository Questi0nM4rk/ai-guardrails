import { buildContext } from "@/commands/context";
import { installPipeline } from "@/pipelines/install";

export async function runInstall(
  projectDir: string,
  flags: Record<string, unknown>,
): Promise<void> {
  const ctx = buildContext(projectDir, flags);
  const result = await installPipeline.run(ctx);
  if (result.status === "error") {
    process.stderr.write(`Error: ${result.message ?? "install failed"}\n`);
    process.exit(2);
  }
}
