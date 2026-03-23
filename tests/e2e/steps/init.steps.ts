import { expect } from "bun:test";
import { Given, Then, When } from "@questi0nm4rk/feats";
import type { E2EWorld } from "./project.steps";

// Base flags used for all E2E init runs:
// --yes         — non-interactive (accept all defaults)
// --no-baseline — skip linter snapshot step (linters may not be installed in CI)
// --no-hooks    — skip lefthook install (lefthook not available in CI)
const BASE_INIT_FLAGS = ["--yes", "--no-baseline", "--no-hooks"];

When<E2EWorld>("I run ai-guardrails init", async (world: E2EWorld) => {
  world.result = await world.project.run(world.binaryPath, [
    "init",
    "--project-dir",
    ".",
    ...BASE_INIT_FLAGS,
  ]);
});

When<E2EWorld>(
  "I run ai-guardrails init with merge strategy",
  async (world: E2EWorld) => {
    world.result = await world.project.run(world.binaryPath, [
      "init",
      "--config-strategy",
      "merge",
      "--project-dir",
      ".",
      ...BASE_INIT_FLAGS,
    ]);
  }
);

When<E2EWorld>(
  "I run ai-guardrails init with replace strategy",
  async (world: E2EWorld) => {
    world.result = await world.project.run(world.binaryPath, [
      "init",
      "--config-strategy",
      "replace",
      "--project-dir",
      ".",
      ...BASE_INIT_FLAGS,
    ]);
  }
);

When<E2EWorld>(
  "I run ai-guardrails init with skip strategy",
  async (world: E2EWorld) => {
    world.result = await world.project.run(world.binaryPath, [
      "init",
      "--config-strategy",
      "skip",
      "--project-dir",
      ".",
      ...BASE_INIT_FLAGS,
    ]);
  }
);

Given<E2EWorld>("ai-guardrails has been initialized", async (world: E2EWorld) => {
  world.result = await world.project.run(world.binaryPath, [
    "init",
    "--project-dir",
    ".",
    ...BASE_INIT_FLAGS,
  ]);
});

Then<E2EWorld>(
  "the exit code should be {int}",
  async (world: E2EWorld, code: unknown) => {
    expect(world.result.exitCode).toBe(Number(code));
  }
);

Then<E2EWorld>(
  "the exit code should not be {int}",
  async (world: E2EWorld, code: unknown) => {
    expect(world.result.exitCode).not.toBe(Number(code));
  }
);

Then<E2EWorld>("{string} should exist", async (world: E2EWorld, file: unknown) => {
  expect(world.project.hasFile(String(file))).toBe(true);
});

Then<E2EWorld>(
  "{string} should contain {string}",
  async (world: E2EWorld, file: unknown, text: unknown) => {
    const content = await world.project.readFile(String(file));
    expect(content).toContain(String(text));
  }
);

Then<E2EWorld>(
  "{string} should not contain {string}",
  async (world: E2EWorld, file: unknown, text: unknown) => {
    const content = await world.project.readFile(String(file));
    expect(content).not.toContain(String(text));
  }
);
