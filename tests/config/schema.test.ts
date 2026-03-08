import { describe, expect, test } from "bun:test";
import { ZodError } from "zod";
import { MachineConfigSchema, ProjectConfigSchema } from "@/config/schema";

describe("MachineConfigSchema", () => {
  test("parses valid machine config", () => {
    const result = MachineConfigSchema.parse({
      profile: "strict",
      ignore: [{ rule: "ruff/E501", reason: "Too strict" }],
    });
    expect(result.profile).toBe("strict");
    expect(result.ignore).toHaveLength(1);
    expect(result.ignore[0]?.rule).toBe("ruff/E501");
  });

  test("defaults profile to standard when omitted", () => {
    const result = MachineConfigSchema.parse({});
    expect(result.profile).toBe("standard");
  });

  test("defaults ignore to empty array when omitted", () => {
    const result = MachineConfigSchema.parse({});
    expect(result.ignore).toEqual([]);
  });

  test("parses all valid profiles", () => {
    expect(MachineConfigSchema.parse({ profile: "strict" }).profile).toBe("strict");
    expect(MachineConfigSchema.parse({ profile: "standard" }).profile).toBe("standard");
    expect(MachineConfigSchema.parse({ profile: "minimal" }).profile).toBe("minimal");
  });

  test("throws ZodError for invalid profile", () => {
    expect(() => MachineConfigSchema.parse({ profile: "extreme" })).toThrow(ZodError);
  });

  test("throws ZodError for ignore entry without reason", () => {
    expect(() =>
      MachineConfigSchema.parse({
        ignore: [{ rule: "ruff/E501" }],
      }),
    ).toThrow(ZodError);
  });

  test("throws ZodError for ignore entry with invalid rule format", () => {
    expect(() =>
      MachineConfigSchema.parse({
        ignore: [{ rule: "E501-invalid", reason: "test" }],
      }),
    ).toThrow(ZodError);
  });

  test("throws ZodError for ignore entry with empty reason", () => {
    expect(() =>
      MachineConfigSchema.parse({
        ignore: [{ rule: "ruff/E501", reason: "" }],
      }),
    ).toThrow(ZodError);
  });
});

describe("ProjectConfigSchema", () => {
  test("parses valid project config with all fields", () => {
    const result = ProjectConfigSchema.parse({
      profile: "minimal",
      config: { line_length: 100, indent_width: 2 },
      ignore: [{ rule: "ruff/D", reason: "No docstrings" }],
      allow: [
        {
          rule: "ruff/ARG002",
          glob: "tests/**/*.py",
          reason: "pytest fixtures",
        },
      ],
    });
    expect(result.profile).toBe("minimal");
    expect(result.config.line_length).toBe(100);
    expect(result.ignore).toHaveLength(1);
    expect(result.allow).toHaveLength(1);
  });

  test("profile is optional (undefined when omitted)", () => {
    const result = ProjectConfigSchema.parse({});
    expect(result.profile).toBeUndefined();
  });

  test("config defaults to empty object with schema defaults", () => {
    const result = ProjectConfigSchema.parse({});
    expect(result.config.line_length).toBe(88);
    expect(result.config.indent_width).toBe(4);
  });

  test("ignore defaults to empty array", () => {
    const result = ProjectConfigSchema.parse({});
    expect(result.ignore).toEqual([]);
  });

  test("allow defaults to empty array", () => {
    const result = ProjectConfigSchema.parse({});
    expect(result.allow).toEqual([]);
  });

  test("throws ZodError for invalid profile", () => {
    expect(() => ProjectConfigSchema.parse({ profile: "ultra" })).toThrow(ZodError);
  });

  test("throws ZodError for line_length below minimum", () => {
    expect(() => ProjectConfigSchema.parse({ config: { line_length: 40 } })).toThrow(ZodError);
  });

  test("throws ZodError for line_length above maximum", () => {
    expect(() => ProjectConfigSchema.parse({ config: { line_length: 300 } })).toThrow(ZodError);
  });

  test("throws ZodError for invalid indent_width", () => {
    expect(() => ProjectConfigSchema.parse({ config: { indent_width: 3 } })).toThrow(ZodError);
  });

  test("python_version is optional", () => {
    const result = ProjectConfigSchema.parse({
      config: { python_version: "3.11" },
    });
    expect(result.config.python_version).toBe("3.11");
  });

  test("allow entry requires glob", () => {
    expect(() =>
      ProjectConfigSchema.parse({
        allow: [{ rule: "ruff/E501", reason: "test" }],
      }),
    ).toThrow(ZodError);
  });

  test("passthrough allows unknown config keys", () => {
    const result = ProjectConfigSchema.parse({
      config: { unknown_tool_setting: 42 },
    });
    expect((result.config as Record<string, unknown>).unknown_tool_setting).toBe(42);
  });
});
