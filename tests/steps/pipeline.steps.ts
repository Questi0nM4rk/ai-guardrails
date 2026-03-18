import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { ALL_GENERATORS } from "@/generators/registry";
import { checkPipeline } from "@/pipelines/check";
import { installPipeline } from "@/pipelines/install";
import type { PipelineContext, PipelineResult } from "@/pipelines/types";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

interface PipelineWorld extends World {
  ctx: PipelineContext;
  result?: PipelineResult;
  inlineResult?: PipelineResult;
}

const BASE_CONFIG = buildResolvedConfig(
  MachineConfigSchema.parse({}),
  ProjectConfigSchema.parse({})
);

function makeRuffIssues(count: number): string {
  return JSON.stringify(
    Array.from({ length: count }, (_, i) => ({
      code: "E501",
      filename: `/project/foo${i}.py`,
      location: { row: i + 1, column: 1 },
      message: "Line too long",
    }))
  );
}

function makeBaseCtx(overrides: Partial<PipelineContext> = {}): PipelineContext {
  const fm = new FakeFileManager();
  fm.seed("/project/pyproject.toml", "[tool.ruff]");

  return {
    projectDir: "/project",
    config: BASE_CONFIG,
    fileManager: fm,
    commandRunner: new FakeCommandRunner(),
    console: new FakeConsole(),
    flags: {},
    ...overrides,
  };
}

function checkExitCode(result: PipelineResult): number {
  if (result.status === "ok") return 0;
  return (result.issueCount ?? 0) > 0 ? 1 : 2;
}

function installExitCode(result: PipelineResult): number {
  return result.status === "error" ? 2 : 0;
}

// ── Given steps ──────────────────────────────────────────────────────────────

Given<PipelineWorld>("a project with no lint issues", async (world: PipelineWorld) => {
  world.ctx = makeBaseCtx();
  (world.ctx.commandRunner as FakeCommandRunner).register(
    ["ruff", "check", "--output-format=json", "/project"],
    { stdout: "[]", stderr: "", exitCode: 0 }
  );
});

function seedLintIssues(world: PipelineWorld, count: number): void {
  world.ctx = makeBaseCtx();
  (world.ctx.commandRunner as FakeCommandRunner).register(
    ["ruff", "check", "--output-format=json", "/project"],
    { stdout: makeRuffIssues(count), stderr: "", exitCode: 1 }
  );
}

Given<PipelineWorld>(
  "a project with {int} lint issue",
  async (world: PipelineWorld, count: unknown) => {
    seedLintIssues(world, Number(count));
  }
);

Given<PipelineWorld>(
  "a project with {int} lint issues",
  async (world: PipelineWorld, count: unknown) => {
    seedLintIssues(world, Number(count));
  }
);

Given<PipelineWorld>(
  "a project with no lint issues and format flag {string}",
  async (world: PipelineWorld, format: unknown) => {
    world.ctx = makeBaseCtx({ flags: { format: String(format) } });
    (world.ctx.commandRunner as FakeCommandRunner).register(
      ["ruff", "check", "--output-format=json", "/project"],
      { stdout: "[]", stderr: "", exitCode: 0 }
    );
  }
);

Given<PipelineWorld>(
  "a check pipeline result with status {string} and issue count {int}",
  async (world: PipelineWorld, status: unknown, count: unknown) => {
    const s = String(status);
    expect(["ok", "error"]).toContain(s);
    world.inlineResult = {
      status: s === "ok" ? "ok" : "error",
      issueCount: Number(count),
    };
  }
);

Given<PipelineWorld>("a default install project", async (world: PipelineWorld) => {
  world.ctx = makeBaseCtx();
});

Given<PipelineWorld>(
  "a default install project with noHooks flag",
  async (world: PipelineWorld) => {
    world.ctx = makeBaseCtx({ flags: { noHooks: true } });
  }
);

Given<PipelineWorld>(
  "a default install project with noCi flag",
  async (world: PipelineWorld) => {
    world.ctx = makeBaseCtx({ flags: { noCi: true } });
  }
);

Given<PipelineWorld>(
  "an install result with status {string}",
  async (world: PipelineWorld, status: unknown) => {
    const s = String(status);
    expect(["ok", "error"]).toContain(s);
    world.inlineResult = { status: s === "ok" ? "ok" : "error" };
  }
);

// ── When steps ───────────────────────────────────────────────────────────────

When<PipelineWorld>("the check pipeline runs", async (world: PipelineWorld) => {
  world.result = await checkPipeline.run(world.ctx);
});

When<PipelineWorld>("the install pipeline runs", async (world: PipelineWorld) => {
  world.result = await installPipeline.run(world.ctx);
});

// ── Then steps ────────────────────────────────────────────────────────────────

Then<PipelineWorld>(
  "the result status should be {string}",
  async (world: PipelineWorld, status: unknown) => {
    const s = String(status);
    expect(["ok", "error"]).toContain(s);
    if (world.result === undefined) throw new Error("result not set");
    expect(world.result.status).toBe(s === "ok" ? "ok" : "error");
  }
);

Then<PipelineWorld>(
  "the result issue count should be {int}",
  async (world: PipelineWorld, count: unknown) => {
    if (world.result === undefined) throw new Error("result not set");
    expect(world.result.issueCount).toBe(Number(count));
  }
);

Then<PipelineWorld>(
  "the result issue count should be greater than 0",
  async (world: PipelineWorld) => {
    if (world.result === undefined) throw new Error("result not set");
    expect(world.result.issueCount ?? 0).toBeGreaterThan(0);
  }
);

Then<PipelineWorld>(
  "the console should have recorded steps",
  async (world: PipelineWorld) => {
    expect((world.ctx.console as FakeConsole).steps.length).toBeGreaterThan(0);
  }
);

Then<PipelineWorld>(
  "the console should have recorded successes",
  async (world: PipelineWorld) => {
    expect((world.ctx.console as FakeConsole).successes.length).toBeGreaterThan(0);
  }
);

Then<PipelineWorld>(
  "the check exit code should be {int}",
  async (world: PipelineWorld, code: unknown) => {
    if (world.result === undefined) throw new Error("result not set");
    expect(checkExitCode(world.result)).toBe(Number(code));
  }
);

Then<PipelineWorld>(
  "the check exit code for that result should be {int}",
  async (world: PipelineWorld, code: unknown) => {
    if (world.inlineResult === undefined) throw new Error("inlineResult not set");
    expect(checkExitCode(world.inlineResult)).toBe(Number(code));
  }
);

Then<PipelineWorld>(
  "at least as many files as generators should be written",
  async (world: PipelineWorld) => {
    const written = (world.ctx.fileManager as FakeFileManager).written;
    expect(written.length).toBeGreaterThanOrEqual(ALL_GENERATORS.length);
  }
);

Then<PipelineWorld>(
  "a file ending with {string} should be written",
  async (world: PipelineWorld, suffix: unknown) => {
    const written = (world.ctx.fileManager as FakeFileManager).written.map(([p]) => p);
    expect(written.some((p) => p.endsWith(String(suffix)))).toBe(true);
  }
);

Then<PipelineWorld>(
  "lefthook install should have been called",
  async (world: PipelineWorld) => {
    const calls = (world.ctx.commandRunner as FakeCommandRunner).calls;
    expect(calls.some((args) => args[0] === "lefthook" && args[1] === "install")).toBe(
      true
    );
  }
);

Then<PipelineWorld>(
  "lefthook install should not have been called",
  async (world: PipelineWorld) => {
    const calls = (world.ctx.commandRunner as FakeCommandRunner).calls;
    expect(calls.some((args) => args[0] === "lefthook" && args[1] === "install")).toBe(
      false
    );
  }
);

Then<PipelineWorld>(
  "a file containing {string} should be written",
  async (world: PipelineWorld, substr: unknown) => {
    const written = (world.ctx.fileManager as FakeFileManager).written.map(([p]) => p);
    expect(written.some((p) => p.includes(String(substr)))).toBe(true);
  }
);

Then<PipelineWorld>(
  "no file containing {string} should be written",
  async (world: PipelineWorld, substr: unknown) => {
    const written = (world.ctx.fileManager as FakeFileManager).written.map(([p]) => p);
    expect(written.some((p) => p.includes(String(substr)))).toBe(false);
  }
);

Then<PipelineWorld>(
  "the install exit code should be {int}",
  async (world: PipelineWorld, code: unknown) => {
    if (world.inlineResult === undefined) throw new Error("inlineResult not set");
    expect(installExitCode(world.inlineResult)).toBe(Number(code));
  }
);
