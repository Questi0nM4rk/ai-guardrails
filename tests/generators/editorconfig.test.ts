import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { editorconfigGenerator } from "@/generators/editorconfig";

function makeConfig(indentWidth?: number) {
  return buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse(
      indentWidth !== undefined ? { config: { indent_width: indentWidth } } : {}
    )
  );
}

describe("editorconfigGenerator", () => {
  test("has correct id", () => {
    expect(editorconfigGenerator.id).toBe("editorconfig");
  });

  test("has correct configFile", () => {
    expect(editorconfigGenerator.configFile).toBe(".editorconfig");
  });

  test("generate returns non-empty string", () => {
    const output = editorconfigGenerator.generate(makeConfig());
    expect(output.length).toBeGreaterThan(0);
  });

  test("generate output matches snapshot with default config", () => {
    const output = editorconfigGenerator.generate(makeConfig());
    expect(output).toMatchSnapshot();
  });

  test("generate output matches snapshot with indent_width 4", () => {
    const output = editorconfigGenerator.generate(makeConfig(4));
    expect(output).toMatchSnapshot();
  });
});
