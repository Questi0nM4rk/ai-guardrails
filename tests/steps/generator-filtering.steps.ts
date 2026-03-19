import { expect } from "bun:test";
import { basename } from "node:path";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import type { ResolvedConfig } from "@/config/schema";
import { agentRulesGenerator } from "@/generators/agent-rules";
import { biomeGenerator } from "@/generators/biome";
import { claudeSettingsGenerator } from "@/generators/claude-settings";
import { codespellGenerator } from "@/generators/codespell";
import { editorconfigGenerator } from "@/generators/editorconfig";
import { lefthookGenerator } from "@/generators/lefthook";
import { markdownlintGenerator } from "@/generators/markdownlint";
import { ruffGenerator } from "@/generators/ruff";
import type { ConfigGenerator } from "@/generators/types";
import { generateConfigsStep } from "@/steps/generate-configs";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";

interface FilteringWorld extends World {
  fm: FakeFileManager;
  detectedLanguages: string[];
  writtenFiles: string[];
  inspectedGenerator: ConfigGenerator | undefined;
  inspectedLanguages: readonly string[] | undefined;
}

function makeDefaultConfig(): ResolvedConfig {
  return {
    profile: "standard",
    ignore: [],
    allow: [],
    values: { line_length: 88, indent_width: 2 },
    ignoredRules: new Set(),
    ignorePaths: [],
    noConsoleLevel: "warn" as const,
    isAllowed: () => false,
  };
}

function makePlugin(id: string) {
  return {
    id,
    name: id,
    detect: async () => true,
    runners: () => [],
  };
}

// ─── Generator inspection Given steps ────────────────────────────────────────

When<FilteringWorld>(
  "the ruff generator languages are inspected",
  (world: FilteringWorld) => {
    world.inspectedGenerator = ruffGenerator;
    world.inspectedLanguages = ruffGenerator.languages;
  }
);

When<FilteringWorld>(
  "the biome generator languages are inspected",
  (world: FilteringWorld) => {
    world.inspectedGenerator = biomeGenerator;
    world.inspectedLanguages = biomeGenerator.languages;
  }
);

When<FilteringWorld>(
  "the lefthook generator languages are inspected",
  (world: FilteringWorld) => {
    world.inspectedGenerator = lefthookGenerator;
    world.inspectedLanguages = lefthookGenerator.languages;
  }
);

When<FilteringWorld>(
  "the claude-settings generator languages are inspected",
  (world: FilteringWorld) => {
    world.inspectedGenerator = claudeSettingsGenerator;
    world.inspectedLanguages = claudeSettingsGenerator.languages;
  }
);

When<FilteringWorld>(
  "the editorconfig generator languages are inspected",
  (world: FilteringWorld) => {
    world.inspectedGenerator = editorconfigGenerator;
    world.inspectedLanguages = editorconfigGenerator.languages;
  }
);

When<FilteringWorld>(
  "the markdownlint generator languages are inspected",
  (world: FilteringWorld) => {
    world.inspectedGenerator = markdownlintGenerator;
    world.inspectedLanguages = markdownlintGenerator.languages;
  }
);

When<FilteringWorld>(
  "the codespell generator languages are inspected",
  (world: FilteringWorld) => {
    world.inspectedGenerator = codespellGenerator;
    world.inspectedLanguages = codespellGenerator.languages;
  }
);

When<FilteringWorld>(
  "the agent-rules generator languages are inspected",
  (world: FilteringWorld) => {
    world.inspectedGenerator = agentRulesGenerator;
    world.inspectedLanguages = agentRulesGenerator.languages;
  }
);

Then<FilteringWorld>(
  "the generator languages should contain {string}",
  (world: FilteringWorld, lang: unknown) => {
    expect(world.inspectedLanguages).toBeDefined();
    expect(world.inspectedLanguages).toContain(String(lang));
  }
);

Then<FilteringWorld>(
  "the generator languages should have length {int}",
  (world: FilteringWorld, len: unknown) => {
    expect(world.inspectedLanguages).toBeDefined();
    expect(world.inspectedLanguages?.length).toBe(Number(len));
  }
);

Then<FilteringWorld>(
  "the generator has no languages field",
  (world: FilteringWorld) => {
    expect(world.inspectedLanguages).toBeUndefined();
  }
);

// ─── Project-with-detected-language Given steps ───────────────────────────────

Given<FilteringWorld>(
  "a project with detected language {string}",
  async (world: FilteringWorld, lang: unknown) => {
    world.fm = new FakeFileManager();
    world.detectedLanguages = [String(lang)];
  }
);

Given<FilteringWorld>(
  "a project with detected languages {string} and {string}",
  async (world: FilteringWorld, langA: unknown, langB: unknown) => {
    world.fm = new FakeFileManager();
    world.detectedLanguages = [String(langA), String(langB)];
  }
);

// ─── When: run generateConfigsStep ───────────────────────────────────────────

When<FilteringWorld>("configs are generated", async (world: FilteringWorld) => {
  const fm = world.fm ?? new FakeFileManager();
  const languages = (world.detectedLanguages ?? []).map(makePlugin);
  await generateConfigsStep(PROJECT_DIR, languages, makeDefaultConfig(), fm, "merge");
  world.writtenFiles = fm.written.map(([p]) => basename(p));
});

// ─── Then: file written / not written ─────────────────────────────────────────

Then<FilteringWorld>(
  "{string} should be written",
  (world: FilteringWorld, file: unknown) => {
    expect(world.writtenFiles).toContain(String(file));
  }
);

Then<FilteringWorld>(
  "{string} should not be written",
  (world: FilteringWorld, file: unknown) => {
    expect(world.writtenFiles).not.toContain(String(file));
  }
);
