import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then } from "@questi0nm4rk/feats";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { generateLefthookConfig } from "@/generators/lefthook";

interface FreshRepoGuardWorld extends World {
  lefthookConfig: string;
}

function makeDefaultConfig() {
  return buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse({})
  );
}

Given<FreshRepoGuardWorld>(
  "a generated lefthook config",
  (world: FreshRepoGuardWorld) => {
    world.lefthookConfig = generateLefthookConfig(makeDefaultConfig(), []);
  }
);

Then<FreshRepoGuardWorld>(
  "the lefthook config should contain {string}",
  (world: FreshRepoGuardWorld, text: unknown) => {
    expect(world.lefthookConfig).toContain(String(text));
  }
);

Then<FreshRepoGuardWorld>(
  "{string} should come before {string} in the no-commits-to-main section",
  (world: FreshRepoGuardWorld, first: unknown, second: unknown) => {
    const noCommitsIdx = world.lefthookConfig.indexOf("no-commits-to-main");
    expect(noCommitsIdx).toBeGreaterThanOrEqual(0);

    // Only look within the no-commits-to-main section
    const section = world.lefthookConfig.slice(noCommitsIdx);
    const firstIdx = section.indexOf(String(first));
    const secondIdx = section.indexOf(String(second));

    expect(firstIdx).toBeGreaterThanOrEqual(0);
    expect(secondIdx).toBeGreaterThanOrEqual(0);
    expect(firstIdx).toBeLessThan(secondIdx);
  }
);
