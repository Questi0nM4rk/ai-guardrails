import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { generateLefthookConfig, LEFTHOOK_GENERATOR_ID } from "@/generators/lefthook";
import { ALL_GENERATORS, applicableGenerators } from "@/generators/registry";
import type { ConfigGenerator } from "@/generators/types";
import { validateConfigsStep } from "@/steps/validate-configs";
import { computeHash } from "@/utils/hash";
import { FakeFileManager } from "../fakes/fake-file-manager";

function makeConfig() {
  const machine = MachineConfigSchema.parse({});
  const project = ProjectConfigSchema.parse({});
  return buildResolvedConfig(machine, project);
}

/**
 * Generate a valid config file body for a generator.
 * lefthookGenerator.generate() intentionally throws — use generateLefthookConfig() instead.
 */
function generateContent(gen: ConfigGenerator): string {
  if (gen.id === LEFTHOOK_GENERATOR_ID) {
    return generateLefthookConfig(makeConfig(), []);
  }
  return gen.generate(makeConfig());
}

/** Seed all generators with valid content */
function seedAllValid(fm: FakeFileManager, projectDir: string): void {
  for (const gen of ALL_GENERATORS) {
    fm.seed(`${projectDir}/${gen.configFile}`, generateContent(gen));
  }
}

/** Seed a config file without any hash header (user-owned) */
function seedUserOwnedConfig(
  fm: FakeFileManager,
  projectDir: string,
  gen: ConfigGenerator
): void {
  fm.seed(
    `${projectDir}/${gen.configFile}`,
    "# user-owned content\nno hash header here\n"
  );
}

/** Get the correct hash header prefix for a config file */
function hashPrefix(configFile: string): string {
  if (configFile.endsWith(".jsonc") || configFile.endsWith(".json")) {
    return "//";
  }
  if (configFile.endsWith(".md")) {
    return "<!--";
  }
  return "#";
}

/** Seed a config file with a hash header that has wrong hash (tampered) */
function seedTamperedConfig(
  fm: FakeFileManager,
  projectDir: string,
  gen: ConfigGenerator
): void {
  const fakeHash = "a".repeat(64);
  const prefix = hashPrefix(gen.configFile);
  const body = "tampered body content\n";
  const header =
    prefix === "<!--"
      ? `<!-- ai-guardrails:sha256=${fakeHash} -->`
      : `${prefix} ai-guardrails:sha256=${fakeHash}`;
  fm.seed(`${projectDir}/${gen.configFile}`, `${header}\n${body}`);
}

describe("validateConfigsStep — all generators", () => {
  test("returns ok when all configs present and valid", async () => {
    const fm = new FakeFileManager();
    seedAllValid(fm, "/project");

    const result = await validateConfigsStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("validated");
  });

  test("returns error when a config file is missing", async () => {
    const fm = new FakeFileManager();
    const [first, ...rest] = ALL_GENERATORS;
    if (!first) throw new Error("No generators defined");

    for (const gen of rest) {
      fm.seed(`/project/${gen.configFile}`, generateContent(gen));
    }
    // first is intentionally absent

    const result = await validateConfigsStep("/project", fm);

    expect(result.status).toBe("error");
    expect(result.message).toContain(`missing: ${first.configFile}`);
  });
});

describe("validateConfigsStep — single generator isolation", () => {
  test("missing config returns error with 'missing: <file>'", async () => {
    const fm = new FakeFileManager();
    // Seed nothing — all files missing

    const result = await validateConfigsStep("/project", fm);

    expect(result.status).toBe("error");
    expect(result.message).toContain("missing:");
  });

  test("config without hash header is ok (user-owned)", async () => {
    const fm = new FakeFileManager();

    for (const gen of ALL_GENERATORS) {
      seedUserOwnedConfig(fm, "/project", gen);
    }

    const result = await validateConfigsStep("/project", fm);

    // User-owned files (no hash header) skip tamper check → ok
    expect(result.status).toBe("ok");
  });

  test("config with hash header but wrong hash returns error with 'tampered'", async () => {
    const fm = new FakeFileManager();

    // Seed all valid except one which we tamper
    const [first, ...rest] = ALL_GENERATORS;
    if (!first) throw new Error("No generators");

    for (const gen of rest) {
      fm.seed(`/project/${gen.configFile}`, generateContent(gen));
    }
    seedTamperedConfig(fm, "/project", first);

    const result = await validateConfigsStep("/project", fm);

    expect(result.status).toBe("error");
    expect(result.message).toContain(`tampered: ${first.configFile}`);
  });

  test("config with valid hash header passes tamper check", async () => {
    const fm = new FakeFileManager();
    const body = "# body content\nsome config = true\n";
    const hash = computeHash(body);
    const validContent = `# ai-guardrails:sha256=${hash}\n${body}`;

    for (const gen of ALL_GENERATORS) {
      fm.seed(`/project/${gen.configFile}`, validContent);
    }

    const result = await validateConfigsStep("/project", fm);

    expect(result.status).toBe("ok");
  });

  test("ok message includes generator count", async () => {
    const fm = new FakeFileManager();
    seedAllValid(fm, "/project");

    const result = await validateConfigsStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(result.message).toContain(String(ALL_GENERATORS.length));
  });
});

describe("validateConfigsStep — activeLanguageIds filter", () => {
  test("only validates generators applicable to the given language IDs", async () => {
    const fm = new FakeFileManager();
    const activeIds = new Set<string>();
    const applicable = applicableGenerators(activeIds);

    for (const gen of applicable) {
      fm.seed(`/project/${gen.configFile}`, generateContent(gen));
    }

    const result = await validateConfigsStep("/project", fm, activeIds);

    expect(result.status).toBe("ok");
  });

  test("reports missing for a language-specific generator when language is active", async () => {
    const fm = new FakeFileManager();

    const languageSpecificGen = ALL_GENERATORS.find(
      (g) => g.languages !== undefined && g.languages.length > 0
    );

    if (!languageSpecificGen?.languages) {
      // No language-specific generators exist; test is a no-op
      return;
    }

    const requiredLanguage = languageSpecificGen.languages[0];
    if (!requiredLanguage) return;

    // Seed all universal generators (no language gate) but not the language-specific one
    const universalGens = applicableGenerators(new Set<string>());
    for (const gen of universalGens) {
      fm.seed(`/project/${gen.configFile}`, generateContent(gen));
    }
    // Intentionally leave languageSpecificGen unseeded

    const result = await validateConfigsStep(
      "/project",
      fm,
      new Set([requiredLanguage])
    );

    expect(result.status).toBe("error");
    expect(result.message).toContain(`missing: ${languageSpecificGen.configFile}`);
  });

  test("returns ok with correct count when activeLanguageIds filters generators", async () => {
    const fm = new FakeFileManager();
    const activeIds = new Set<string>(["python"]);
    const applicable = applicableGenerators(activeIds);

    for (const gen of applicable) {
      fm.seed(`/project/${gen.configFile}`, generateContent(gen));
    }

    const result = await validateConfigsStep("/project", fm, activeIds);

    expect(result.status).toBe("ok");
    expect(result.message).toContain(String(applicable.length));
  });

  test("empty activeLanguageIds only validates language-agnostic generators", async () => {
    const fm = new FakeFileManager();
    const activeIds = new Set<string>();
    const applicable = applicableGenerators(activeIds);

    for (const gen of applicable) {
      fm.seed(`/project/${gen.configFile}`, generateContent(gen));
    }

    // Do NOT seed language-specific generators — they should not be checked
    const result = await validateConfigsStep("/project", fm, activeIds);

    expect(result.status).toBe("ok");
    expect(result.message).toContain(String(applicable.length));
  });
});
