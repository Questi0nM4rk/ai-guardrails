import { expect } from "bun:test";
import { Given, Then, When } from "@questi0nm4rk/feats";
import { ALL_GENERATORS } from "@/generators/registry";
import { installPipeline } from "@/pipelines/install";
import type { FakeCommandRunner } from "../fakes/fake-command-runner";
import type { FakeFileManager } from "../fakes/fake-file-manager";
import { installExitCode, makeBaseCtx, type PipelineWorld } from "./pipeline-shared";

// ── Given steps ──────────────────────────────────────────────────────────────

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

When<PipelineWorld>("the install pipeline runs", async (world: PipelineWorld) => {
  world.result = await installPipeline.run(world.ctx);
});

// ── Then steps ────────────────────────────────────────────────────────────────

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

Then<PipelineWorld>(
  "at least as many files as generators should be written",
  async (world: PipelineWorld) => {
    const written = (world.ctx.fileManager as FakeFileManager).written;
    expect(written.length).toBeGreaterThanOrEqual(ALL_GENERATORS.length);
  }
);
