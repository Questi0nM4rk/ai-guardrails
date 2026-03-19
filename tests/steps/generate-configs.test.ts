import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { ALL_GENERATORS } from "@/generators/registry";
import type { LanguagePlugin } from "@/languages/types";
import { generateConfigsStep } from "@/steps/generate-configs";
import { FakeFileManager } from "../fakes/fake-file-manager";

function makeConfig() {
  const machine = MachineConfigSchema.parse({});
  const project = ProjectConfigSchema.parse({});
  return buildResolvedConfig(machine, project);
}

function makePlugin(id: string): LanguagePlugin {
  return { id, name: id, detect: async () => true, runners: () => [] };
}

/** Number of universal generators (no languages gate) */
const UNIVERSAL_COUNT = ALL_GENERATORS.filter((g) => g.languages === undefined).length;

describe("generateConfigsStep", () => {
  test("writes only universal generators when no languages detected", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    const result = await generateConfigsStep("/project", [], config, fm);

    expect(result.status).toBe("ok");
    expect(fm.written.length).toBe(UNIVERSAL_COUNT);
  });

  test("writes all generators when all gated languages are active", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();
    const languages = [makePlugin("python"), makePlugin("typescript")];

    const result = await generateConfigsStep("/project", languages, config, fm);

    expect(result.status).toBe("ok");
    expect(fm.written.length).toBe(ALL_GENERATORS.length);
  });

  test("ruff generator runs for python-only project", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    await generateConfigsStep("/project", [makePlugin("python")], config, fm);

    const paths = fm.written.map(([p]) => p);
    expect(paths.some((p) => p.endsWith("ruff.toml"))).toBe(true);
    expect(paths.some((p) => p.endsWith("biome.jsonc"))).toBe(false);
  });

  test("biome generator runs for typescript-only project", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    await generateConfigsStep("/project", [makePlugin("typescript")], config, fm);

    const paths = fm.written.map(([p]) => p);
    expect(paths.some((p) => p.endsWith("biome.jsonc"))).toBe(true);
    expect(paths.some((p) => p.endsWith("ruff.toml"))).toBe(false);
  });

  test("neither ruff nor biome run for language-only project without python/typescript", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    await generateConfigsStep("/project", [makePlugin("rust")], config, fm);

    const paths = fm.written.map(([p]) => p);
    expect(paths.some((p) => p.endsWith("ruff.toml"))).toBe(false);
    expect(paths.some((p) => p.endsWith("biome.jsonc"))).toBe(false);
  });

  test("each written file path is under the projectDir", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    await generateConfigsStep("/project", [], config, fm);

    for (const [path] of fm.written) {
      expect(path.startsWith("/project/")).toBe(true);
    }
  });

  test("written files have non-empty content", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    await generateConfigsStep("/project", [], config, fm);

    for (const [, content] of fm.written) {
      expect(content.length).toBeGreaterThan(0);
    }
  });

  test("result message lists generated files", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    const result = await generateConfigsStep("/project", [], config, fm);

    expect(result.message).toContain("Generated");
    expect(result.message).toContain(String(UNIVERSAL_COUNT));
  });
});
