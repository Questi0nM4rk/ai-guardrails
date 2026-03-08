import { describe, expect, test } from "bun:test";
import { checkPipeline } from "@/pipelines/check";
import type { PipelineContext } from "@/pipelines/types";
import { FakeFileManager } from "../fakes/fake-file-manager";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { buildResolvedConfig, MachineConfigSchema, ProjectConfigSchema } from "@/config/schema";

function makeCtx(overrides: Partial<PipelineContext> = {}): PipelineContext {
  const machine = MachineConfigSchema.parse({});
  const project = ProjectConfigSchema.parse({});
  const config = buildResolvedConfig(machine, project);
  const fm = new FakeFileManager();
  // Python project — needed for language detection
  fm.seed("/project/pyproject.toml", "[tool.ruff]");

  return {
    projectDir: "/project",
    languages: [],
    config,
    fileManager: fm,
    commandRunner: new FakeCommandRunner(),
    console: new FakeConsole(),
    flags: {},
    ...overrides,
  };
}

describe("checkPipeline", () => {
  test("returns ok when runners produce no issues", async () => {
    const ctx = makeCtx();
    // Ruff returns no issues (empty array JSON)
    (ctx.commandRunner as FakeCommandRunner).register(
      ["ruff", "check", "--output-format=json", "/project"],
      { stdout: "[]", stderr: "", exitCode: 0 },
    );

    const result = await checkPipeline.run(ctx);

    expect(result.status).toBe("ok");
  });

  test("returns error when runners produce issues", async () => {
    const ctx = makeCtx();
    const ruffOutput = JSON.stringify([
      {
        code: "E501",
        filename: "/project/foo.py",
        location: { row: 1, column: 1 },
        message: "Line too long",
      },
    ]);
    (ctx.commandRunner as FakeCommandRunner).register(
      ["ruff", "check", "--output-format=json", "/project"],
      { stdout: ruffOutput, stderr: "", exitCode: 1 },
    );

    const result = await checkPipeline.run(ctx);

    expect(result.status).toBe("error");
    expect(result.issueCount).toBeGreaterThan(0);
  });

  test("reports steps to console", async () => {
    const ctx = makeCtx();
    const cons = ctx.console as FakeConsole;

    await checkPipeline.run(ctx);

    expect(cons.steps.length).toBeGreaterThan(0);
  });
});
