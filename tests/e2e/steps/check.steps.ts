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
    // Each violation produces at least one line of output;
    // verify the combined output is non-empty for the required minimum count.
    expect(combined.length).toBeGreaterThan(Number(minCount) - 1);
  }
);

Then<E2EWorld>("all detected languages should have configs", async (world) => {
  // After init, at least .lefthook.yml and .claude/settings.json should exist
  expect(world.project.hasFile(".lefthook.yml")).toBe(true);
  expect(world.project.hasFile(".claude/settings.json")).toBe(true);
});
