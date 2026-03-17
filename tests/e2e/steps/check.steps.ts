import { expect } from "bun:test";
import { Then, When } from "@questi0nm4rk/feats";
import type { E2EWorld } from "./project.steps";

When<E2EWorld>("I run ai-guardrails check", async (world) => {
  world.result = await world.project.run(world.binaryPath, [
    "check",
    "--project-dir",
    ".",
  ]);
});

Then<E2EWorld>(
  "the output should contain at least {int} violation",
  async (world, minCount: unknown) => {
    const combined = world.result.stdout + world.result.stderr;
    // Each violation occupies at least one non-empty line of output.
    const violationLines = combined
      .split("\n")
      .filter((line) => line.trim().length > 0);
    expect(violationLines.length).toBeGreaterThanOrEqual(Number(minCount));
  }
);

Then<E2EWorld>("global guardrails configs should exist", async (world) => {
  // After init, global configs that are language-independent must be present.
  expect(world.project.hasFile("lefthook.yml")).toBe(true);
  expect(world.project.hasFile(".claude/settings.json")).toBe(true);
});
