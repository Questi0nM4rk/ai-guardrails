import { describe, expect, test } from "bun:test";
import { loadMachineConfig, loadProjectConfig, resolveConfig } from "@/config/loader";
import { FakeFileManager } from "../fakes/fake-file-manager";

describe("loadMachineConfig", () => {
  test("loads and parses valid machine config from TOML", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      "/machine.toml",
      `profile = "strict"\n[[ignore]]\nrule = "ruff/E501"\nreason = "Too strict"\n`,
    );
    const config = await loadMachineConfig("/machine.toml", fm);
    expect(config.profile).toBe("strict");
    expect(config.ignore).toHaveLength(1);
    expect(config.ignore[0]?.rule).toBe("ruff/E501");
  });

  test("returns defaults when file does not exist", async () => {
    const fm = new FakeFileManager();
    const config = await loadMachineConfig("/nonexistent.toml", fm);
    expect(config.profile).toBe("standard");
    expect(config.ignore).toEqual([]);
  });

  test("returns defaults for empty TOML file", async () => {
    const fm = new FakeFileManager();
    fm.seed("/empty.toml", "");
    const config = await loadMachineConfig("/empty.toml", fm);
    expect(config.profile).toBe("standard");
  });
});

describe("loadProjectConfig", () => {
  test("loads project config from project directory", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      "/proj/.ai-guardrails/config.toml",
      `profile = "minimal"\n[config]\nline_length = 100\n`,
    );
    const config = await loadProjectConfig("/proj", fm);
    expect(config.profile).toBe("minimal");
    expect(config.config.line_length).toBe(100);
  });

  test("returns defaults when project config does not exist", async () => {
    const fm = new FakeFileManager();
    const config = await loadProjectConfig("/proj", fm);
    expect(config.profile).toBeUndefined();
    expect(config.ignore).toEqual([]);
  });
});

describe("resolveConfig", () => {
  test("project profile overrides machine profile", () => {
    const resolved = resolveConfig(
      { profile: "strict", ignore: [] },
      { profile: "minimal", config: { line_length: 88, indent_width: 4 }, ignore: [], allow: [] },
    );
    expect(resolved.profile).toBe("minimal");
  });

  test("uses machine profile when project has none", () => {
    const resolved = resolveConfig(
      { profile: "strict", ignore: [] },
      { config: { line_length: 88, indent_width: 4 }, ignore: [], allow: [] },
    );
    expect(resolved.profile).toBe("strict");
  });

  test("merges ignore lists from machine and project", () => {
    const resolved = resolveConfig(
      {
        profile: "standard",
        ignore: [{ rule: "ruff/E501", reason: "machine" }],
      },
      {
        config: { line_length: 88, indent_width: 4 },
        ignore: [{ rule: "ruff/D", reason: "project" }],
        allow: [],
      },
    );
    expect(resolved.ignore).toHaveLength(2);
    const rules = resolved.ignore.map((i) => i.rule);
    expect(rules).toContain("ruff/E501");
    expect(rules).toContain("ruff/D");
  });

  test("project ignore overrides machine ignore reason for same rule", () => {
    const resolved = resolveConfig(
      {
        profile: "standard",
        ignore: [{ rule: "ruff/E501", reason: "machine reason" }],
      },
      {
        config: { line_length: 88, indent_width: 4 },
        ignore: [{ rule: "ruff/E501", reason: "project reason" }],
        allow: [],
      },
    );
    expect(resolved.ignore).toHaveLength(1);
    expect(resolved.ignore[0]?.reason).toBe("project reason");
  });

  test("isAllowed returns true for globally ignored rule", () => {
    const resolved = resolveConfig(
      { profile: "standard", ignore: [{ rule: "ruff/E501", reason: "test" }] },
      { config: { line_length: 88, indent_width: 4 }, ignore: [], allow: [] },
    );
    expect(resolved.isAllowed("ruff/E501", "src/foo.py")).toBe(true);
  });

  test("isAllowed returns false for non-ignored rule", () => {
    const resolved = resolveConfig(
      { profile: "standard", ignore: [] },
      { config: { line_length: 88, indent_width: 4 }, ignore: [], allow: [] },
    );
    expect(resolved.isAllowed("ruff/E501", "src/foo.py")).toBe(false);
  });

  test("isAllowed returns true when rule matches glob allow entry", () => {
    const resolved = resolveConfig(
      { profile: "standard", ignore: [] },
      {
        config: { line_length: 88, indent_width: 4 },
        ignore: [],
        allow: [{ rule: "ruff/ARG002", glob: "tests/**/*.py", reason: "fixtures" }],
      },
    );
    expect(resolved.isAllowed("ruff/ARG002", "tests/unit/foo.py")).toBe(true);
    expect(resolved.isAllowed("ruff/ARG002", "src/foo.py")).toBe(false);
  });

  test("isAllowed is false for different rule matching allow glob", () => {
    const resolved = resolveConfig(
      { profile: "standard", ignore: [] },
      {
        config: { line_length: 88, indent_width: 4 },
        ignore: [],
        allow: [{ rule: "ruff/ARG002", glob: "tests/**/*.py", reason: "fixtures" }],
      },
    );
    expect(resolved.isAllowed("ruff/E501", "tests/unit/foo.py")).toBe(false);
  });

  test("ignoredRules set contains all globally ignored rules", () => {
    const resolved = resolveConfig(
      {
        profile: "standard",
        ignore: [{ rule: "ruff/E501", reason: "test" }],
      },
      {
        config: { line_length: 88, indent_width: 4 },
        ignore: [{ rule: "ruff/D", reason: "project" }],
        allow: [],
      },
    );
    expect(resolved.ignoredRules.has("ruff/E501")).toBe(true);
    expect(resolved.ignoredRules.has("ruff/D")).toBe(true);
    expect(resolved.ignoredRules.has("ruff/W")).toBe(false);
  });
});
