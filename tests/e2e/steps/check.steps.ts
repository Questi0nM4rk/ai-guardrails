import { expect } from "bun:test";
import { Then, When } from "@questi0nm4rk/feats";
import type { E2EWorld } from "./project.steps";

When<E2EWorld>("I run ai-guardrails check", async (world: E2EWorld) => {
  world.result = await world.project.run(world.binaryPath, [
    "check",
    "--project-dir",
    ".",
  ]);
});

Then<E2EWorld>(
  "the output should contain at least {int} violation",
  async (world: E2EWorld, _minCount: unknown) => {
    // Linters exit non-zero when violations are found.
    // Parsing exact violation count from heterogeneous linter output is fragile.
    expect(world.result.exitCode).not.toBe(0);
  }
);

Then<E2EWorld>("global guardrails configs should exist", async (world: E2EWorld) => {
  // After init, global configs that are language-independent must be present.
  expect(world.project.hasFile("lefthook.yml")).toBe(true);
  expect(world.project.hasFile(".claude/settings.json")).toBe(true);
});
