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
  "the check should complete without config error",
  async (world: E2EWorld) => {
    // Exit 0 = no issues (or tools skipped), exit 1 = lint violations found.
    // Exit 2 = config error (broken). Both 0 and 1 are valid depending on tool availability.
    expect(world.result.exitCode).not.toBe(2);
  }
);

Then<E2EWorld>("global guardrails configs should exist", async (world: E2EWorld) => {
  // After init, global configs that are language-independent must be present.
  expect(world.project.hasFile("lefthook.yml")).toBe(true);
  expect(world.project.hasFile(".claude/settings.json")).toBe(true);
});
