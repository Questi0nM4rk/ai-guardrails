import { describe, expect, test } from "bun:test";
import { installPipeline } from "@/pipelines/install";
import type { PipelineContext } from "@/pipelines/types";
import { FakeFileManager } from "../fakes/fake-file-manager";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { buildResolvedConfig, MachineConfigSchema, ProjectConfigSchema } from "@/config/schema";
import { ALL_GENERATORS } from "@/generators/registry";

function makeCtx(overrides: Partial<PipelineContext> = {}): PipelineContext {
  const machine = MachineConfigSchema.parse({});
  const project = ProjectConfigSchema.parse({});
  const config = buildResolvedConfig(machine, project);
  const fm = new FakeFileManager();
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

describe("installPipeline", () => {
  test("returns ok and writes all config files", async () => {
    const ctx = makeCtx();

    const result = await installPipeline.run(ctx);

    expect(result.status).toBe("ok");
    const writtenPaths = (ctx.fileManager as FakeFileManager).written.map(([p]) => p);
    // At minimum all generators should have written files
    expect(writtenPaths.length).toBeGreaterThanOrEqual(ALL_GENERATORS.length);
  });

  test("writes lefthook.yml", async () => {
    const ctx = makeCtx();

    await installPipeline.run(ctx);

    const writtenPaths = (ctx.fileManager as FakeFileManager).written.map(([p]) => p);
    const hasLefthook = writtenPaths.some((p) => p.endsWith("lefthook.yml"));
    expect(hasLefthook).toBe(true);
  });

  test("runs lefthook install", async () => {
    const ctx = makeCtx();
    const cr = ctx.commandRunner as FakeCommandRunner;

    await installPipeline.run(ctx);

    const hasLefthookInstall = cr.calls.some(
      (args) => args[0] === "lefthook" && args[1] === "install",
    );
    expect(hasLefthookInstall).toBe(true);
  });

  test("writes CI workflow file", async () => {
    const ctx = makeCtx();

    await installPipeline.run(ctx);

    const writtenPaths = (ctx.fileManager as FakeFileManager).written.map(([p]) => p);
    const hasCi = writtenPaths.some((p) => p.includes("ai-guardrails.yml"));
    expect(hasCi).toBe(true);
  });

  test("skips hooks when noHooks flag is set", async () => {
    const ctx = makeCtx({ flags: { noHooks: true } });
    const cr = ctx.commandRunner as FakeCommandRunner;

    await installPipeline.run(ctx);

    const hasLefthookInstall = cr.calls.some(
      (args) => args[0] === "lefthook" && args[1] === "install",
    );
    expect(hasLefthookInstall).toBe(false);
  });

  test("skips CI when noCi flag is set", async () => {
    const ctx = makeCtx({ flags: { noCi: true } });

    await installPipeline.run(ctx);

    const writtenPaths = (ctx.fileManager as FakeFileManager).written.map(([p]) => p);
    const hasCi = writtenPaths.some((p) => p.includes("ai-guardrails.yml"));
    expect(hasCi).toBe(false);
  });

  test("reports progress steps to console", async () => {
    const ctx = makeCtx();
    const cons = ctx.console as FakeConsole;

    await installPipeline.run(ctx);

    expect(cons.steps.length).toBeGreaterThan(0);
    expect(cons.successes.length).toBeGreaterThan(0);
  });
});
