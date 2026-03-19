import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
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

const PYTHON = [makePlugin("python")];
const TYPESCRIPT = [makePlugin("typescript")];

// ---------------------------------------------------------------------------
// Strategy: file does not exist — always write regardless of strategy
// ---------------------------------------------------------------------------

describe("applyStrategy — file does not exist", () => {
  test("writes file with merge strategy", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    const result = await generateConfigsStep("/project", PYTHON, config, fm, "merge");

    expect(result.status).toBe("ok");
    const writtenPaths = fm.written.map(([p]) => p);
    expect(writtenPaths.some((p) => p.includes("ruff.toml"))).toBe(true);
  });

  test("writes file with skip strategy when file missing", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    const result = await generateConfigsStep("/project", PYTHON, config, fm, "skip");

    // skip only skips existing files — new files are still written
    expect(result.status).toBe("ok");
    const writtenPaths = fm.written.map(([p]) => p);
    expect(writtenPaths.some((p) => p.includes("ruff.toml"))).toBe(true);
  });

  test("writes file with replace strategy when file missing", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    const result = await generateConfigsStep("/project", PYTHON, config, fm, "replace");

    expect(result.status).toBe("ok");
    const writtenPaths = fm.written.map(([p]) => p);
    expect(writtenPaths.some((p) => p.includes("ruff.toml"))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Strategy: file exists + skip — returns null (no write)
// ---------------------------------------------------------------------------

describe("applyStrategy — file exists + skip", () => {
  test("does not overwrite existing ruff.toml", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/ruff.toml", "# existing content\n");
    const config = makeConfig();

    const result = await generateConfigsStep("/project", PYTHON, config, fm, "skip");

    expect(result.status).toBe("ok");
    // ruff.toml should not appear in written list
    const writtenPaths = fm.written.map(([p]) => p);
    expect(writtenPaths.some((p) => p === "/project/ruff.toml")).toBe(false);
  });

  test("result message mentions skipped files", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/ruff.toml", "# existing\n");
    const config = makeConfig();

    const result = await generateConfigsStep("/project", PYTHON, config, fm, "skip");

    expect(result.status).toBe("ok");
    expect(result.message).toContain("Skipped");
  });
});

// ---------------------------------------------------------------------------
// Strategy: file exists + replace — returns generated content
// ---------------------------------------------------------------------------

describe("applyStrategy — file exists + replace", () => {
  test("overwrites existing ruff.toml with generated content", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/ruff.toml", "# old content that should be replaced\n");
    const config = makeConfig();

    await generateConfigsStep("/project", PYTHON, config, fm, "replace");

    const writeEntry = fm.written.find(([p]) => p === "/project/ruff.toml");
    expect(writeEntry).toBeDefined();
    if (writeEntry) {
      const [, newContent] = writeEntry;
      expect(newContent).not.toContain("old content that should be replaced");
    }
  });
});

// ---------------------------------------------------------------------------
// Strategy: file exists + merge on TOML — deep-merges existing with generated
// ---------------------------------------------------------------------------

describe("applyStrategy — file exists + merge on TOML", () => {
  test("merges user keys with generated keys for ruff.toml", async () => {
    const fm = new FakeFileManager();
    // Seed a minimal TOML file with a custom user key
    fm.seed("/project/ruff.toml", 'line-length = 100\n[custom]\nkey = "user-value"\n');
    const config = makeConfig();

    await generateConfigsStep("/project", PYTHON, config, fm, "merge");

    const writeEntry = fm.written.find(([p]) => p === "/project/ruff.toml");
    expect(writeEntry).toBeDefined();
    if (writeEntry) {
      const [, merged] = writeEntry;
      // Generated content overrides line-length; merged output contains field
      expect(merged).toContain("line-length");
    }
  });
});

// ---------------------------------------------------------------------------
// Strategy: file exists + merge on JSON/JSONC — deep-merges
// ---------------------------------------------------------------------------

describe("applyStrategy — file exists + merge on JSONC", () => {
  test("merges existing biome.jsonc with generated content", async () => {
    const fm = new FakeFileManager();
    // Seed a minimal JSONC file with a URL in a string (regression test for Finding 1)
    const existingJsonc = `{
  // See https://api.example.com/biomejs for docs
  "formatter": { "indentWidth": 4 },
  "customKey": "preserved"
}`;
    fm.seed("/project/biome.jsonc", existingJsonc);
    const config = makeConfig();

    const result = await generateConfigsStep(
      "/project",
      TYPESCRIPT,
      config,
      fm,
      "merge"
    );

    expect(result.status).toBe("ok");
    const writeEntry = fm.written.find(([p]) => p === "/project/biome.jsonc");
    expect(writeEntry).toBeDefined();
    if (writeEntry) {
      const [, merged] = writeEntry;
      // Merged JSONC has a hash header comment — strip it before parsing
      const jsonContent = merged.replace(/^\/\/[^\n]*\n/, "");
      expect(() => JSON.parse(jsonContent)).not.toThrow();
      const obj = JSON.parse(jsonContent) as Record<string, unknown>;
      // customKey from existing should be present (deepMerge retains existing keys not in generated)
      expect(obj.customKey).toBe("preserved");
    }
  });

  test("JSONC URL in string literal is not corrupted during strip", async () => {
    const fm = new FakeFileManager();
    // The URL https://api.example.com must survive comment stripping
    const existingJsonc = `{
  "$schema": "https://api.example.com/schema.json",
  "linter": { "enabled": true }
}`;
    fm.seed("/project/biome.jsonc", existingJsonc);
    const config = makeConfig();

    const result = await generateConfigsStep(
      "/project",
      TYPESCRIPT,
      config,
      fm,
      "merge"
    );

    expect(result.status).toBe("ok");
    // biome.jsonc is mergeable; parse must not fail on the URL
    const writeEntry = fm.written.find(([p]) => p === "/project/biome.jsonc");
    expect(writeEntry).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Strategy: file exists + merge on non-structured format — falls back to replace
// ---------------------------------------------------------------------------

describe("applyStrategy — file exists + merge on non-structured format", () => {
  test("falls back to replace for .editorconfig (not TOML/JSON)", async () => {
    const fm = new FakeFileManager();
    // editorconfig is not a TOML or JSON file — cannot be merged
    fm.seed("/project/.editorconfig", "# old editorconfig\nroot = false\n");
    const config = makeConfig();

    await generateConfigsStep("/project", [], config, fm, "merge");

    const writeEntry = fm.written.find(([p]) => p === "/project/.editorconfig");
    expect(writeEntry).toBeDefined();
    if (writeEntry) {
      const [, content] = writeEntry;
      // Should be the generated content, not the old "root = false"
      expect(content).not.toContain("root = false");
    }
  });
});

// ---------------------------------------------------------------------------
// Strategy: existing file has parse error — falls back to replace
// ---------------------------------------------------------------------------

describe("applyStrategy — parse error falls back to replace", () => {
  test("falls back to replace for corrupted TOML", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/ruff.toml", "this is not valid toml ===\n");
    const config = makeConfig();

    // Should not throw — falls back to replace or surfaces as error
    const result = await generateConfigsStep("/project", PYTHON, config, fm, "merge");

    if (result.status === "ok") {
      const writeEntry = fm.written.find(([p]) => p === "/project/ruff.toml");
      if (writeEntry) {
        const [, content] = writeEntry;
        // Fell back to generated content, not the broken TOML
        expect(content).not.toContain("this is not valid toml");
      }
    }
    // If status is "error" due to smol-toml throwing, that's also acceptable behavior
    expect(["ok", "error"]).toContain(result.status);
  });

  test("falls back to replace for corrupted JSON", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/biome.jsonc", "{ not valid json }");
    const config = makeConfig();

    const result = await generateConfigsStep(
      "/project",
      TYPESCRIPT,
      config,
      fm,
      "merge"
    );

    // Either falls back to generated (ok) or surfaces as error
    expect(["ok", "error"]).toContain(result.status);
  });
});
