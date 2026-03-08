import { buildContext } from "@/commands/context";
import { generatePipeline } from "@/pipelines/generate";

export async function runGenerate(
  projectDir: string,
  flags: Record<string, unknown>,
): Promise<void> {
  const ctx = buildContext(projectDir, flags);
  const result = await generatePipeline.run(ctx);
  if (result.status === "error") {
    process.stderr.write(`Error: ${result.message ?? "generate failed"}\n`);
    process.exit(2);
  }
}
