import { expect } from "bun:test";
import { Given, Then, When } from "@questi0nm4rk/feats";
import { installPipeline } from "@/pipelines/install";
import type { FakeCommandRunner } from "../fakes/fake-command-runner";
import type { FakeFileManager } from "../fakes/fake-file-manager";
import { installExitCode, makeBaseCtx, type PipelineWorld } from "./pipeline-shared";

Given<PipelineWorld>("a default install project", async (world: PipelineWorld) => {
  world.ctx = makeBaseCtx();
});

Given<PipelineWorld>(
  "an install result with status {string}",
  async (world: PipelineWorld, status: unknown) => {
    const s = String(status);
    expect(["ok", "error"]).toContain(s);
    world.inlineResult = { status: s === "ok" ? "ok" : "error" };
  }
);

When<PipelineWorld>("the install pipeline runs", async (world: PipelineWorld) => {
  world.result = await installPipeline.run(world.ctx);
});

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
  "no project files should be written",
  async (world: PipelineWorld) => {
    const written = (world.ctx.fileManager as FakeFileManager).written.map(([p]) => p);
    expect(written).toHaveLength(0);
  }
);

Then<PipelineWorld>(
  "no file ending with {string} should be written",
  async (world: PipelineWorld, suffix: unknown) => {
    const written = (world.ctx.fileManager as FakeFileManager).written.map(([p]) => p);
    expect(written.some((p) => p.endsWith(String(suffix)))).toBe(false);
  }
);

Then<PipelineWorld>(
  "the install exit code should be {int}",
  async (world: PipelineWorld, code: unknown) => {
    if (world.inlineResult === undefined) throw new Error("inlineResult not set");
    expect(installExitCode(world.inlineResult)).toBe(Number(code));
  }
);
