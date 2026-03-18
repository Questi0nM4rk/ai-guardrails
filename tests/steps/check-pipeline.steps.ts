import { expect } from "bun:test";
import { Given, Then, When } from "@questi0nm4rk/feats";
import { checkPipeline } from "@/pipelines/check";
import type { FakeCommandRunner } from "../fakes/fake-command-runner";
import type { FakeConsole } from "../fakes/fake-console";
import {
  checkExitCode,
  makeBaseCtx,
  makeRuffIssues,
  type PipelineWorld,
} from "./pipeline-shared";

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

// ── When steps ───────────────────────────────────────────────────────────────

When<PipelineWorld>("the check pipeline runs", async (world: PipelineWorld) => {
  world.result = await checkPipeline.run(world.ctx);
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
