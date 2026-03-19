import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { markdownlintGenerator } from "@/generators/markdownlint";

function makeConfig() {
  return buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse({})
  );
}

describe("markdownlintGenerator", () => {
  test("has correct id", () => {
    expect(markdownlintGenerator.id).toBe("markdownlint");
  });

  test("has correct configFile", () => {
    expect(markdownlintGenerator.configFile).toBe(".markdownlint.jsonc");
  });

  test("generate returns non-empty string", () => {
    const output = markdownlintGenerator.generate(makeConfig());
    expect(output.length).toBeGreaterThan(0);
  });

  test("generate output contains valid JSON body", () => {
    const output = markdownlintGenerator.generate(makeConfig());
    // Strip the JSONC hash header comment line(s) to get the JSON body
    const jsonBody = output
      .split("\n")
      .filter((line) => !line.startsWith("//"))
      .join("\n")
      .trim();
    expect(() => JSON.parse(jsonBody)).not.toThrow();
  });

  test("generate output matches snapshot", () => {
    const output = markdownlintGenerator.generate(makeConfig());
    expect(output).toMatchSnapshot();
  });
});
