import { expect } from "bun:test";
import { Given, Then, When } from "@questi0nm4rk/feats";
import type { E2EWorld } from "./project.steps";

When<E2EWorld>("I run ai-guardrails init", async (world) => {
  world.result = await world.project.run(world.binaryPath, [
    "init",

    "--project-dir",
    ".",
  ]);
});

When<E2EWorld>("I run ai-guardrails init with merge strategy", async (world) => {
  world.result = await world.project.run(world.binaryPath, [
    "init",

    "--config-strategy",
    "merge",
    "--project-dir",
    ".",
  ]);
});

When<E2EWorld>("I run ai-guardrails init with replace strategy", async (world) => {
  world.result = await world.project.run(world.binaryPath, [
    "init",

    "--config-strategy",
    "replace",
    "--project-dir",
    ".",
  ]);
});

When<E2EWorld>("I run ai-guardrails init with skip strategy", async (world) => {
  world.result = await world.project.run(world.binaryPath, [
    "init",

    "--config-strategy",
    "skip",
    "--project-dir",
    ".",
  ]);
});

Given<E2EWorld>("ai-guardrails has been initialized", async (world) => {
  world.result = await world.project.run(world.binaryPath, [
    "init",

    "--project-dir",
    ".",
  ]);
});

Then<E2EWorld>("the exit code should be {int}", async (world, code: unknown) => {
  expect(world.result.exitCode).toBe(Number(code));
});

Then<E2EWorld>("the exit code should not be {int}", async (world, code: unknown) => {
  expect(world.result.exitCode).not.toBe(Number(code));
});

Then<E2EWorld>("{string} should exist", async (world, file: unknown) => {
  expect(world.project.hasFile(String(file))).toBe(true);
});

Then<E2EWorld>(
  "{string} should contain {string}",
  async (world, file: unknown, text: unknown) => {
    const content = await world.project.readFile(String(file));
    expect(content).toContain(String(text));
  }
);
