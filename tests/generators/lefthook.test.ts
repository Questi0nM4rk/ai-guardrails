import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import {
  generateLefthookConfig,
  LEFTHOOK_GENERATOR_ID,
  lefthookGenerator,
} from "@/generators/lefthook";
import { makePlugin } from "../fakes/fake-language-plugin";

function makeConfig(ignorePaths?: string[]) {
  return buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse(
      ignorePaths !== undefined && ignorePaths.length > 0
        ? { ignore_paths: ignorePaths }
        : {}
    )
  );
}

describe("lefthookGenerator", () => {
  test("has correct id", () => {
    expect(lefthookGenerator.id).toBe(LEFTHOOK_GENERATOR_ID);
    expect(lefthookGenerator.id).toBe("lefthook");
  });

  test("has correct configFile", () => {
    expect(lefthookGenerator.configFile).toBe("lefthook.yml");
  });

  test("generate() throws — direct call not supported", () => {
    expect(() => lefthookGenerator.generate(makeConfig())).toThrow(
      "lefthookGenerator.generate() must not be called directly"
    );
  });
});

describe("generateLefthookConfig", () => {
  test("returns non-empty string", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output.length).toBeGreaterThan(0);
  });

  test("output contains pre-commit section", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain("pre-commit:");
  });

  test("output contains commit-msg section", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain("commit-msg:");
  });

  test("output contains gitleaks command", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain("gitleaks:");
  });

  test("output contains codespell command", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain("codespell:");
  });

  test("output contains markdownlint command", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain("markdownlint:");
  });

  test("includes biome-fix when TypeScript plugin active", () => {
    const output = generateLefthookConfig(makeConfig(), [makePlugin("typescript")]);
    expect(output).toContain("biome-fix:");
  });

  test("does not include biome-fix when TypeScript plugin absent", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).not.toContain("biome-fix:");
  });

  test("includes ruff-fix when Python plugin active", () => {
    const output = generateLefthookConfig(makeConfig(), [makePlugin("python")]);
    expect(output).toContain("ruff-fix:");
  });

  test("does not include ruff-fix when Python plugin absent", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).not.toContain("ruff-fix:");
  });

  test("includes both biome-fix and ruff-fix when TypeScript and Python active", () => {
    const output = generateLefthookConfig(makeConfig(), [
      makePlugin("typescript"),
      makePlugin("python"),
    ]);
    expect(output).toContain("biome-fix:");
    expect(output).toContain("ruff-fix:");
  });

  test("output matches snapshot with no active plugins", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toMatchSnapshot();
  });

  test("output matches snapshot with TypeScript plugin", () => {
    const output = generateLefthookConfig(makeConfig(), [makePlugin("typescript")]);
    expect(output).toMatchSnapshot();
  });

  test("output matches snapshot with Python plugin", () => {
    const output = generateLefthookConfig(makeConfig(), [makePlugin("python")]);
    expect(output).toMatchSnapshot();
  });

  test("output matches snapshot with TypeScript and Python plugins", () => {
    const output = generateLefthookConfig(makeConfig(), [
      makePlugin("typescript"),
      makePlugin("python"),
    ]);
    expect(output).toMatchSnapshot();
  });

  test("no-commits-to-main script includes fresh repo guard", () => {
    const output = generateLefthookConfig(makeConfig(), []);
    expect(output).toContain("git rev-list --count HEAD >/dev/null 2>&1 || exit 0");
    const revListIndex = output.indexOf("git rev-list --count HEAD");
    const branchIndex = output.indexOf("git rev-parse --abbrev-ref HEAD");
    expect(revListIndex).toBeGreaterThan(-1);
    expect(branchIndex).toBeGreaterThan(-1);
    expect(revListIndex).toBeLessThan(branchIndex);
  });

  test("output contains exclude when ignorePaths configured", () => {
    const output = generateLefthookConfig(makeConfig(["vendor/**"]), []);
    expect(output).toContain("exclude:");
  });

  test("output matches snapshot with ignorePaths", () => {
    const output = generateLefthookConfig(makeConfig(["vendor/**", "dist/**"]), []);
    expect(output).toMatchSnapshot();
  });
});
