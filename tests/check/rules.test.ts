import { describe, expect, test } from "bun:test";
import {
  ALL_RULE_GROUPS,
  COMMAND_RULES,
  collectCommandRules,
  collectDenyGlobs,
  DANGEROUS_DENY_GLOBS,
} from "@/check/rules/groups";
import { DEFAULT_PATH_RULES } from "@/check/rules/paths";
import { buildRuleSet } from "@/check/ruleset";

describe("COMMAND_RULES (backward-compat export)", () => {
  test("does not contain a RecurseRule (injected by buildRuleSet)", () => {
    expect(COMMAND_RULES.some((r) => r.kind === "recurse")).toBe(false);
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

describe("ALL_RULE_GROUPS", () => {
  test("has 6 groups", () => {
    expect(ALL_RULE_GROUPS).toHaveLength(6);
  });

  test("each group has an id and name", () => {
    for (const group of ALL_RULE_GROUPS) {
      expect(group.id).toBeTruthy();
      expect(group.name).toBeTruthy();
    }
  });

  test("each group has at least one commandRule", () => {
    for (const group of ALL_RULE_GROUPS) {
      expect(group.commandRules.length).toBeGreaterThan(0);
    }
  });

  test("collectCommandRules aggregates all group rules", () => {
    const rules = collectCommandRules(ALL_RULE_GROUPS);
    const totalFromGroups = ALL_RULE_GROUPS.reduce(
      (sum, g) => sum + g.commandRules.length,
      0
    );
    expect(rules).toHaveLength(totalFromGroups);
  });

  test("collectDenyGlobs aggregates all group globs", () => {
    const globs = collectDenyGlobs(ALL_RULE_GROUPS);
    const totalFromGroups = ALL_RULE_GROUPS.reduce(
      (sum, g) => sum + g.denyGlobs.length,
      0
    );
    expect(globs).toHaveLength(totalFromGroups);
  });

  test("DANGEROUS_DENY_GLOBS matches collectDenyGlobs output", () => {
    expect(DANGEROUS_DENY_GLOBS).toEqual(collectDenyGlobs(ALL_RULE_GROUPS));
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

  test("injects recurseRule into commandRules", () => {
    const rs = buildRuleSet({});
    expect(rs.commandRules.some((r) => r.kind === "recurse")).toBe(true);
  });

  test("adds protectWrite for custom managedFiles", () => {
    const rs = buildRuleSet({ managedFiles: ["custom.lock"] });
    const r = rs.pathRules.find(
      (r) => r.event === "write" && r.pattern.test("custom.lock")
    );
    expect(r).toBeDefined();
  });
});
