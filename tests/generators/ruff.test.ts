import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { ruffGenerator } from "@/generators/ruff";

function makeConfig(profile?: "strict" | "standard" | "minimal") {
  return buildResolvedConfig(
    MachineConfigSchema.parse({ profile: profile ?? "standard" }),
    ProjectConfigSchema.parse({})
  );
}

describe("ruffGenerator", () => {
  test("has correct id", () => {
    expect(ruffGenerator.id).toBe("ruff");
  });

  test("has correct configFile", () => {
    expect(ruffGenerator.configFile).toBe("ruff.toml");
  });

  test("is scoped to python language", () => {
    expect(ruffGenerator.languages).toEqual(["python"]);
  });

  test("strict profile selects ALL rules", () => {
    const output = ruffGenerator.generate(makeConfig("strict"));
    expect(output).toContain('select = ["ALL"]');
  });

  test("standard profile selects recommended ruleset", () => {
    const output = ruffGenerator.generate(makeConfig("standard"));
    expect(output).toContain(
      'select = ["E", "F", "W", "I", "UP", "S", "B", "A", "C4", "ICN", "PIE", "PT", "RSE", "SIM", "TID"]'
    );
    expect(output).not.toContain('select = ["ALL"]');
    expect(output).not.toContain('select = ["E", "F", "S"]');
  });

  test("minimal profile selects only critical rules", () => {
    const output = ruffGenerator.generate(makeConfig("minimal"));
    expect(output).toContain('select = ["E", "F", "S"]');
    expect(output).not.toContain('select = ["ALL"]');
  });

  test("profiles produce different select lines", () => {
    const strict = ruffGenerator.generate(makeConfig("strict"));
    const standard = ruffGenerator.generate(makeConfig("standard"));
    const minimal = ruffGenerator.generate(makeConfig("minimal"));
    expect(strict).not.toBe(standard);
    expect(standard).not.toBe(minimal);
    expect(strict).not.toBe(minimal);
  });

  test("includes banned-api section", () => {
    const output = ruffGenerator.generate(makeConfig("standard"));
    expect(output).toContain("[lint.flake8-tidy-imports.banned-api]");
    expect(output).toContain('"typing.Optional".msg');
    expect(output).toContain('"typing.Union".msg');
    expect(output).toContain('"typing.List".msg');
    expect(output).toContain('"typing.Dict".msg');
    expect(output).toContain('"typing.Set".msg');
    expect(output).toContain('"typing.Tuple".msg');
  });

  test("includes flake8-bugbear section", () => {
    const output = ruffGenerator.generate(makeConfig("standard"));
    expect(output).toContain("[lint.flake8-bugbear]");
    expect(output).toContain(
      'extend-immutable-calls = ["fastapi.Depends", "fastapi.Query", "fastapi.Path"]'
    );
  });

  test("includes flake8-quotes section", () => {
    const output = ruffGenerator.generate(makeConfig("standard"));
    expect(output).toContain("[lint.flake8-quotes]");
    expect(output).toContain('inline-quotes = "double"');
    expect(output).toContain('multiline-quotes = "double"');
    expect(output).toContain('docstring-quotes = "double"');
  });

  test("includes flake8-pytest-style section", () => {
    const output = ruffGenerator.generate(makeConfig("standard"));
    expect(output).toContain("[lint.flake8-pytest-style]");
    expect(output).toContain("fixture-parentheses = true");
    expect(output).toContain("mark-parentheses = true");
    expect(output).toContain('parametrize-names-type = "csv"');
    expect(output).toContain('parametrize-values-type = "list"');
    expect(output).toContain(
      'raises-require-match-for = ["ValueError", "TypeError", "KeyError", "RuntimeError"]'
    );
  });

  test("strict profile removes T201 from ignore list", () => {
    const strict = ruffGenerator.generate(makeConfig("strict"));
    const standard = ruffGenerator.generate(makeConfig("standard"));
    expect(strict).not.toContain('"T201"');
    expect(strict).not.toContain('"S101"');
    expect(strict).not.toContain('"ERA001"');
    expect(standard).toContain('"T201"');
    expect(standard).toContain('"S101"');
    expect(standard).toContain('"ERA001"');
  });

  test("strict output matches snapshot", () => {
    expect(ruffGenerator.generate(makeConfig("strict"))).toMatchSnapshot();
  });

  test("standard output matches snapshot", () => {
    expect(ruffGenerator.generate(makeConfig("standard"))).toMatchSnapshot();
  });

  test("minimal output matches snapshot", () => {
    expect(ruffGenerator.generate(makeConfig("minimal"))).toMatchSnapshot();
  });
});
