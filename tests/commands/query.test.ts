import { describe, expect, test } from "bun:test";
import { queryAllowEntries } from "@/commands/query";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

// FakeFileManager seeds use relative paths and glob returns them relative.
// We use an empty projectDir so join("", relative) === relative, matching
// the seeded keys directly.
const PROJECT_DIR = "";

describe("queryAllowEntries", () => {
  test("reports no config-level allows when config is absent", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    await queryAllowEntries(PROJECT_DIR, "biome/noConsole", fm, cons);

    expect(cons.infos.some((m) => m.includes("No config-level allows"))).toBe(true);
  });

  test("reports no inline allows when no source files exist", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    await queryAllowEntries(PROJECT_DIR, "biome/noConsole", fm, cons);

    expect(cons.infos.some((m) => m.includes("No inline allows"))).toBe(true);
  });

  test("reports config-level allow when matching entry exists", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();
    fm.seed(
      ".ai-guardrails/config.toml",
      `[[allow]]\nrule = "biome/noConsole"\nglob = "src/**"\nreason = "CLI tool"\n`
    );

    await queryAllowEntries(PROJECT_DIR, "biome/noConsole", fm, cons);

    expect(cons.infos.some((m) => m.includes("Config-level allows"))).toBe(true);
    expect(cons.infos.some((m) => m.includes("src/**"))).toBe(true);
    expect(cons.infos.some((m) => m.includes("CLI tool"))).toBe(true);
  });

  test("does not report config allow for a different rule", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();
    fm.seed(
      ".ai-guardrails/config.toml",
      `[[allow]]\nrule = "ruff/E501"\nglob = "**/*.py"\nreason = "URL too long"\n`
    );

    await queryAllowEntries(PROJECT_DIR, "biome/noConsole", fm, cons);

    expect(
      cons.infos.some((m) => m.includes("Config-level allows for biome/noConsole:"))
    ).toBe(false);
    expect(cons.infos.some((m) => m.includes("No config-level allows"))).toBe(true);
  });

  test("reports inline allow found in source file", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();
    fm.seed(
      "src/foo.ts",
      '// ai-guardrails-allow biome/noConsole "CLI tool uses console"\nconsole.log("hi");\n'
    );

    await queryAllowEntries(PROJECT_DIR, "biome/noConsole", fm, cons);

    expect(
      cons.infos.some((m) => m.includes("Inline allows for biome/noConsole"))
    ).toBe(true);
    expect(cons.infos.some((m) => m.includes("src/foo.ts"))).toBe(true);
  });

  test("does not report inline allow for a different rule", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();
    fm.seed(
      "src/foo.ts",
      '// ai-guardrails-allow ruff/E501 "URL too long"\nsome_long_line = 1\n'
    );

    await queryAllowEntries(PROJECT_DIR, "biome/noConsole", fm, cons);

    expect(
      cons.infos.some((m) => m.includes("Inline allows for biome/noConsole"))
    ).toBe(false);
    expect(cons.infos.some((m) => m.includes("No inline allows"))).toBe(true);
  });

  test("reports not suppressed anywhere when neither config nor inline match", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    await queryAllowEntries(PROJECT_DIR, "biome/noConsole", fm, cons);

    expect(cons.infos.some((m) => m.includes("is not suppressed anywhere"))).toBe(true);
  });

  test("does not report not-suppressed when a config match exists", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();
    fm.seed(
      ".ai-guardrails/config.toml",
      `[[allow]]\nrule = "biome/noConsole"\nglob = "src/**"\nreason = "CLI"\n`
    );

    await queryAllowEntries(PROJECT_DIR, "biome/noConsole", fm, cons);

    expect(cons.infos.some((m) => m.includes("is not suppressed anywhere"))).toBe(
      false
    );
  });

  test("reports line number for inline allow", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();
    fm.seed(
      "src/bar.ts",
      'const x = 1;\n// ai-guardrails-allow biome/noConsole "reason"\nconsole.log(x);\n'
    );

    await queryAllowEntries(PROJECT_DIR, "biome/noConsole", fm, cons);

    // The allow comment is on line 2
    expect(cons.infos.some((m) => m.includes(":2"))).toBe(true);
  });

  test("inline allow reason is included in output", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();
    fm.seed(
      "src/cli.ts",
      '// ai-guardrails-allow biome/noConsole "CLI entrypoint needs stdout"\nconsole.log("hi");\n'
    );

    await queryAllowEntries(PROJECT_DIR, "biome/noConsole", fm, cons);

    expect(cons.infos.some((m) => m.includes("CLI entrypoint needs stdout"))).toBe(
      true
    );
  });
});
