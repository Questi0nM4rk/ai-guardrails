import { describe, expect, test } from "bun:test";
import {
  ALL_RULE_GROUPS,
  collectCommandRules,
  collectDenyGlobs,
} from "@/check/rules/groups";

describe("ALL_RULE_GROUPS", () => {
  test("contains 6 groups", () => {
    expect(ALL_RULE_GROUPS.length).toBe(6);
  });

  test("each group has a unique id", () => {
    const ids = ALL_RULE_GROUPS.map((g) => g.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  test("each group has at least one command rule", () => {
    for (const group of ALL_RULE_GROUPS) {
      expect(group.commandRules.length).toBeGreaterThan(0);
    }
  });

  test("each group has at least one deny glob", () => {
    for (const group of ALL_RULE_GROUPS) {
      expect(group.denyGlobs.length).toBeGreaterThan(0);
    }
  });

  test("expected group ids present", () => {
    const ids = ALL_RULE_GROUPS.map((g) => g.id);
    expect(ids).toContain("destructive-rm");
    expect(ids).toContain("git-force-push");
    expect(ids).toContain("git-destructive");
    expect(ids).toContain("git-bypass-hooks");
    expect(ids).toContain("chmod-world-writable");
    expect(ids).toContain("remote-code-exec");
  });
});

describe("collectCommandRules", () => {
  test("returns all rules from given groups", () => {
    const rules = collectCommandRules(ALL_RULE_GROUPS);
    expect(rules.length).toBeGreaterThan(0);
  });

  test("returns empty for empty groups", () => {
    expect(collectCommandRules([])).toEqual([]);
  });

  test("returns only rules from selected groups", () => {
    const rmGroup = ALL_RULE_GROUPS.filter((g) => g.id === "destructive-rm");
    const rules = collectCommandRules(rmGroup);
    expect(rules.length).toBe(1);
    const first = rules[0];
    expect(first).toBeDefined();
    if (first !== undefined && first.kind === "call") {
      expect(first.cmd).toBe("rm");
    }
  });
});

describe("collectDenyGlobs", () => {
  test("collects all globs from all groups", () => {
    const globs = collectDenyGlobs(ALL_RULE_GROUPS);
    const expected = ALL_RULE_GROUPS.reduce((sum, g) => sum + g.denyGlobs.length, 0);
    expect(globs.length).toBe(expected);
  });

  test("returns empty for empty groups", () => {
    expect(collectDenyGlobs([])).toEqual([]);
  });
});
