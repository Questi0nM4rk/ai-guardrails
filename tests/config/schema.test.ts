import { describe, expect, test } from "bun:test";
import { ZodError } from "zod";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";

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
      })
    ).toThrow(ZodError);
  });

  test("throws ZodError for ignore entry with invalid rule format", () => {
    expect(() =>
      MachineConfigSchema.parse({
        ignore: [{ rule: "E501-invalid", reason: "test" }],
      })
    ).toThrow(ZodError);
  });

  test("throws ZodError for ignore entry with empty reason", () => {
    expect(() =>
      MachineConfigSchema.parse({
        ignore: [{ rule: "ruff/E501", reason: "" }],
      })
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
    expect(result.config.indent_width).toBe(2);
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
    expect(() => ProjectConfigSchema.parse({ config: { line_length: 40 } })).toThrow(
      ZodError
    );
  });

  test("throws ZodError for line_length above maximum", () => {
    expect(() => ProjectConfigSchema.parse({ config: { line_length: 300 } })).toThrow(
      ZodError
    );
  });

  test("throws ZodError for invalid indent_width", () => {
    expect(() => ProjectConfigSchema.parse({ config: { indent_width: 3 } })).toThrow(
      ZodError
    );
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
      })
    ).toThrow(ZodError);
  });

  test("passthrough allows unknown config keys", () => {
    const result = ProjectConfigSchema.parse({
      config: { unknown_tool_setting: 42 },
    });
    expect((result.config as Record<string, unknown>).unknown_tool_setting).toBe(42);
  });
});

describe("buildResolvedConfig", () => {
  function makeMachine(overrides?: object) {
    return MachineConfigSchema.parse({ profile: "standard", ...overrides });
  }

  function makeProject(overrides?: object) {
    return ProjectConfigSchema.parse(overrides ?? {});
  }

  test("uses project profile when set", () => {
    const resolved = buildResolvedConfig(
      makeMachine(),
      makeProject({ profile: "strict" })
    );
    expect(resolved.profile).toBe("strict");
  });

  test("falls back to machine profile when project profile is absent", () => {
    const resolved = buildResolvedConfig(
      makeMachine({ profile: "minimal" }),
      makeProject()
    );
    expect(resolved.profile).toBe("minimal");
  });

  test("merges machine and project ignore lists, deduped by rule", () => {
    const machine = makeMachine({
      ignore: [{ rule: "ruff/E501", reason: "machine" }],
    });
    const project = makeProject({
      ignore: [
        { rule: "ruff/E501", reason: "project override" },
        { rule: "ruff/W291", reason: "trailing whitespace" },
      ],
    });
    const resolved = buildResolvedConfig(machine, project);
    // ruff/E501 deduped — project reason wins (last write)
    expect(resolved.ignore).toHaveLength(2);
    const e501 = resolved.ignore.find((e) => e.rule === "ruff/E501");
    expect(e501?.reason).toBe("project override");
  });

  test("isAllowed returns true for ignored rule", () => {
    const machine = makeMachine({
      ignore: [{ rule: "ruff/E501", reason: "test" }],
    });
    const resolved = buildResolvedConfig(machine, makeProject());
    expect(resolved.isAllowed("ruff/E501", "any/file.py")).toBe(true);
  });

  test("isAllowed returns false for non-ignored rule", () => {
    const resolved = buildResolvedConfig(makeMachine(), makeProject());
    expect(resolved.isAllowed("ruff/E501", "any/file.py")).toBe(false);
  });

  test("resolved values include typed fields", () => {
    const project = makeProject({ config: { line_length: 100, indent_width: 2 } });
    const resolved = buildResolvedConfig(makeMachine(), project);
    expect(resolved.values.line_length).toBe(100);
    expect(resolved.values.indent_width).toBe(2);
  });

  test("resolved values preserve passthrough (unknown) config keys", () => {
    // Fix 8: passthrough keys were dropped by the previous explicit-copy approach
    const project = makeProject({ config: { custom_tool_option: "hello" } });
    const resolved = buildResolvedConfig(makeMachine(), project);
    expect((resolved.values as Record<string, unknown>).custom_tool_option).toBe(
      "hello"
    );
  });

  test("resolved values include python_version when set", () => {
    const project = makeProject({ config: { python_version: "3.11" } });
    const resolved = buildResolvedConfig(makeMachine(), project);
    expect(resolved.values.python_version).toBe("3.11");
  });

  test("resolved values omit python_version when not set", () => {
    const resolved = buildResolvedConfig(makeMachine(), makeProject());
    expect(resolved.values.python_version).toBeUndefined();
  });
});
