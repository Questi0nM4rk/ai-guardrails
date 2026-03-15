import { describe, expect, test } from "bun:test";
import { COMMAND_RULES } from "@/check/rules/commands";
import { DEFAULT_PATH_RULES } from "@/check/rules/paths";
import { buildRuleSet } from "@/check/ruleset";

describe("COMMAND_RULES", () => {
  test("contains a RecurseRule", () => {
    expect(COMMAND_RULES.some((r) => r.kind === "recurse")).toBe(true);
  });

  test("contains rm CallRule with --recursive and --force flags", () => {
    const r = COMMAND_RULES.find(
      (r) =>
        r.kind === "call" &&
        r.cmd === "rm" &&
        r.flags?.includes("--recursive") &&
        r.flags?.includes("--force")
    );
    expect(r).toBeDefined();
  });
});

describe("DEFAULT_PATH_RULES", () => {
  test("has rule matching .env for write", () => {
    const r = DEFAULT_PATH_RULES.find(
      (r) => r.event === "write" && r.pattern.test(".env")
    );
    expect(r).toBeDefined();
  });

  test("has rule matching .ssh/ for read", () => {
    const r = DEFAULT_PATH_RULES.find(
      (r) => r.event === "read" && r.pattern.test("/home/user/.ssh/id_rsa")
    );
    expect(r).toBeDefined();
  });
});

describe("buildRuleSet", () => {
  test("returns default rules with empty config", () => {
    const rs = buildRuleSet({});
    expect(rs.commandRules.length).toBeGreaterThan(0);
    expect(rs.pathRules.length).toBeGreaterThan(0);
  });

  test("adds protectWrite for custom managedFiles", () => {
    const rs = buildRuleSet({ managedFiles: ["custom.lock"] });
    const r = rs.pathRules.find(
      (r) => r.event === "write" && r.pattern.test("custom.lock")
    );
    expect(r).toBeDefined();
  });
});
