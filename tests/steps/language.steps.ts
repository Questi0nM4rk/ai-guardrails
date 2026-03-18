import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import { ALL_PLUGINS, detectLanguages } from "@/languages/registry";
import type { LanguagePlugin } from "@/languages/types";
import type { StepResult } from "@/models/step-result";
import { detectLanguagesStep } from "@/steps/detect-languages";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";

interface LanguageWorld extends World {
  fm: FakeFileManager;
  detectedIds: string[];
  runnerIds: string[];
  stepResult?: StepResult;
  stepLanguages?: LanguagePlugin[];
}

// "a project with file {string}" and "an empty project" are registered in
// generator.steps.ts — no duplicate registration here.

Given<LanguageWorld>(
  "a project with files {string} and {string}",
  async (world: LanguageWorld, fileA: unknown, fileB: unknown) => {
    world.fm = new FakeFileManager();
    world.fm.seed(`${PROJECT_DIR}/${String(fileA)}`, "content");
    world.fm.seed(`${PROJECT_DIR}/${String(fileB)}`, "content");
  }
);

When<LanguageWorld>("languages are detected", async (world: LanguageWorld) => {
  const plugins = await detectLanguages(PROJECT_DIR, world.fm);
  world.detectedIds = plugins.map((p) => p.id);
});

When<LanguageWorld>(
  "the plugin registry is inspected",
  async (world: LanguageWorld) => {
    world.detectedIds = ALL_PLUGINS.map((p) => p.id);
  }
);

When<LanguageWorld>("the detect-languages step runs", async (world: LanguageWorld) => {
  const { result, languages } = await detectLanguagesStep(PROJECT_DIR, world.fm);
  world.stepResult = result;
  world.stepLanguages = languages;
});

Then<LanguageWorld>(
  "{string} should be detected",
  async (world: LanguageWorld, lang: unknown) => {
    expect(world.detectedIds).toContain(String(lang));
  }
);

Then<LanguageWorld>(
  "only {string} should be detected",
  async (world: LanguageWorld, lang: unknown) => {
    expect(world.detectedIds).toHaveLength(1);
    expect(world.detectedIds[0]).toBe(String(lang));
  }
);

Then<LanguageWorld>(
  "it should contain {int} plugins",
  async (world: LanguageWorld, count: unknown) => {
    expect(world.detectedIds).toHaveLength(Number(count));
  }
);

Then<LanguageWorld>(
  "the last plugin id should be {string}",
  async (world: LanguageWorld, id: unknown) => {
    const last = world.detectedIds[world.detectedIds.length - 1];
    expect(last).toBe(String(id));
  }
);

Then<LanguageWorld>("all plugin ids should be unique", async (world: LanguageWorld) => {
  const unique = new Set(world.detectedIds);
  expect(unique.size).toBe(world.detectedIds.length);
});

Then<LanguageWorld>(
  "{string} should appear before {string}",
  async (world: LanguageWorld, first: unknown, second: unknown) => {
    const firstIdx = world.detectedIds.indexOf(String(first));
    const secondIdx = world.detectedIds.indexOf(String(second));
    expect(firstIdx).toBeLessThan(secondIdx);
  }
);

Then<LanguageWorld>(
  "the step result status should be {string}",
  async (world: LanguageWorld, status: unknown) => {
    if (world.stepResult === undefined) throw new Error("stepResult not set");
    expect(String(world.stepResult.status)).toBe(String(status));
  }
);

Then<LanguageWorld>(
  "{string} should be in the step languages",
  async (world: LanguageWorld, lang: unknown) => {
    if (world.stepLanguages === undefined) throw new Error("stepLanguages not set");
    const ids = world.stepLanguages.map((l) => l.id);
    expect(ids).toContain(String(lang));
  }
);

Then<LanguageWorld>(
  "the step result message should contain {string}",
  async (world: LanguageWorld, text: unknown) => {
    if (world.stepResult === undefined) throw new Error("stepResult not set");
    expect(world.stepResult.message).toContain(String(text));
  }
);

When<LanguageWorld>(
  "the {string} plugin runners are inspected",
  async (world: LanguageWorld, pluginId: unknown) => {
    const plugin = ALL_PLUGINS.find((p) => p.id === String(pluginId));
    if (plugin === undefined) throw new Error(`Plugin not found: ${String(pluginId)}`);
    world.runnerIds = plugin.runners().map((r) => r.id);
  }
);

Then<LanguageWorld>(
  "the runner ids should include {string}",
  async (world: LanguageWorld, runnerId: unknown) => {
    expect(world.runnerIds).toContain(String(runnerId));
  }
);

Then<LanguageWorld>(
  "there should be {int} runners",
  async (world: LanguageWorld, count: unknown) => {
    expect(world.runnerIds.length).toBe(Number(count));
  }
);
