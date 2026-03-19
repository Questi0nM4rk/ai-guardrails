import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { ALL_GENERATORS } from "@/generators/registry";
import { generateConfigsStep } from "@/steps/generate-configs";
import { withHashHeader, withJsoncHashHeader } from "@/utils/hash";
import { FakeFileManager } from "../fakes/fake-file-manager";
import { makePlugin } from "../fakes/fake-language-plugin";

function makeConfig() {
  const machine = MachineConfigSchema.parse({});
  const project = ProjectConfigSchema.parse({});
  return buildResolvedConfig(machine, project);
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

  describe("stale config cleanup on replace strategy", () => {
    test("deletes biome.jsonc with hash header when python-only project uses replace", async () => {
      const fm = new FakeFileManager();
      const config = makeConfig();
      fm.seed("/project/biome.jsonc", withJsoncHashHeader("{ }\n"));

      const result = await generateConfigsStep(
        "/project",
        [makePlugin("python")],
        config,
        fm,
        "replace"
      );

      expect(result.status).toBe("ok");
      expect(fm.deleted).toContain("/project/biome.jsonc");
      expect(result.message).toContain("Removed 1 stale config(s)");
      expect(result.message).toContain("biome.jsonc");
    });

    test("preserves biome.jsonc without hash header when python-only project uses replace", async () => {
      const fm = new FakeFileManager();
      const config = makeConfig();
      fm.seed("/project/biome.jsonc", "{ /* user-created */ }\n");

      const result = await generateConfigsStep(
        "/project",
        [makePlugin("python")],
        config,
        fm,
        "replace"
      );

      expect(result.status).toBe("ok");
      expect(fm.deleted).not.toContain("/project/biome.jsonc");
    });

    test("does not delete stale biome.jsonc when strategy is merge", async () => {
      const fm = new FakeFileManager();
      const config = makeConfig();
      fm.seed("/project/biome.jsonc", withJsoncHashHeader("{ }\n"));

      const result = await generateConfigsStep(
        "/project",
        [makePlugin("python")],
        config,
        fm,
        "merge"
      );

      expect(result.status).toBe("ok");
      expect(fm.deleted).not.toContain("/project/biome.jsonc");
    });

    test("deletes ruff.toml with hash header when typescript-only project uses replace", async () => {
      const fm = new FakeFileManager();
      const config = makeConfig();
      fm.seed("/project/ruff.toml", withHashHeader("# ruff config\n"));

      const result = await generateConfigsStep(
        "/project",
        [makePlugin("typescript")],
        config,
        fm,
        "replace"
      );

      expect(result.status).toBe("ok");
      expect(fm.deleted).toContain("/project/ruff.toml");
    });

    test("FakeFileManager.deleted tracks all deletions", async () => {
      const fm = new FakeFileManager();
      const config = makeConfig();
      fm.seed("/project/biome.jsonc", withJsoncHashHeader("{ }\n"));
      fm.seed("/project/ruff.toml", withHashHeader("# ruff config\n"));

      await generateConfigsStep("/project", [], config, fm, "replace");

      // With no active languages, all language-gated generators are inactive.
      // Both files have hash headers so both should be deleted.
      expect(fm.deleted).toContain("/project/biome.jsonc");
      expect(fm.deleted).toContain("/project/ruff.toml");
    });
  });
});
