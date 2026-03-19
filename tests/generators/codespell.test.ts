import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { codespellGenerator } from "@/generators/codespell";

function makeConfig() {
  return buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse({})
  );
}

describe("codespellGenerator", () => {
  test("has correct id", () => {
    expect(codespellGenerator.id).toBe("codespell");
  });

  test("has correct configFile", () => {
    expect(codespellGenerator.configFile).toBe(".codespellrc");
  });

  test("generate returns non-empty string", () => {
    const output = codespellGenerator.generate(makeConfig());
    expect(output.length).toBeGreaterThan(0);
  });

  test("generate output matches snapshot", () => {
    const output = codespellGenerator.generate(makeConfig());
    expect(output).toMatchSnapshot();
  });
});
