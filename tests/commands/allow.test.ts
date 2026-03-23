import { describe, expect, test } from "bun:test";
import { appendAllowEntry, escapeTOMLString } from "@/commands/allow";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

describe("escapeTOMLString", () => {
  test("returns plain string unchanged", () => {
    expect(escapeTOMLString("src/**/*.ts")).toBe("src/**/*.ts");
  });

  test("escapes backslashes", () => {
    expect(escapeTOMLString("src\\foo\\bar")).toBe("src\\\\foo\\\\bar");
  });

  test("escapes double-quotes", () => {
    expect(escapeTOMLString('say "hello"')).toBe('say \\"hello\\"');
  });

  test("escapes backslash before double-quote", () => {
    expect(escapeTOMLString('path\\"value')).toBe('path\\\\\\"value');
  });
});

describe("appendAllowEntry", () => {
  test("creates config file when it does not exist", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    await appendAllowEntry(
      "/project",
      "biome/noConsole",
      "src/**/*.ts",
      "CLI tool",
      fm,
      cons
    );

    expect(fm.written).toHaveLength(1);
    const [path, content] = fm.written[0] ?? ["", ""];
    expect(path).toBe("/project/.ai-guardrails/config.toml");
    expect(content).toContain('rule = "biome/noConsole"');
    expect(content).toContain('glob = "src/**/*.ts"');
    expect(content).toContain('reason = "CLI tool"');
  });

  test("appends to existing config file", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();
    fm.seed("/project/.ai-guardrails/config.toml", 'profile = "standard"\n');

    await appendAllowEntry(
      "/project",
      "ruff/E501",
      "**/*.py",
      "URL too long",
      fm,
      cons
    );

    expect(fm.appended).toHaveLength(1);
    const [, appended] = fm.appended[0] ?? ["", ""];
    expect(appended).toContain("[[allow]]");
    expect(appended).toContain('rule = "ruff/E501"');
    expect(appended).toContain('glob = "**/*.py"');
    expect(appended).toContain('reason = "URL too long"');
  });

  test("emits success message", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    await appendAllowEntry("/project", "biome/noConsole", "src/**", "reason", fm, cons);

    expect(cons.successes).toHaveLength(1);
    expect(cons.successes[0]).toContain("biome/noConsole");
    expect(cons.successes[0]).toContain("src/**");
  });

  test("escapes double-quotes in glob before writing TOML", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    await appendAllowEntry(
      "/project",
      "biome/noConsole",
      'src/"weird"/**',
      "reason",
      fm,
      cons
    );

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toContain('glob = "src/\\"weird\\"/**"');
  });

  test("escapes double-quotes in reason before writing TOML", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    await appendAllowEntry(
      "/project",
      "biome/noConsole",
      "src/**",
      'reason with "quotes"',
      fm,
      cons
    );

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toContain('reason = "reason with \\"quotes\\""');
  });

  test("escapes backslashes in glob before writing TOML", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();

    await appendAllowEntry(
      "/project",
      "biome/noConsole",
      "src\\foo",
      "reason",
      fm,
      cons
    );

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toContain('glob = "src\\\\foo"');
  });
});
