import { describe, expect, test } from "bun:test";
import { CHMOD_GROUP } from "@/check/rules/chmod";
import { GIT_DESTRUCTIVE_GROUP } from "@/check/rules/git-destructive";
import { GIT_PUSH_GROUP } from "@/check/rules/git-push";
import { GIT_WORKFLOW_GROUP } from "@/check/rules/git-workflow";
import {
  ALL_RULE_GROUPS,
  collectCommandRules,
  collectDenyGlobs,
} from "@/check/rules/groups";
import { REMOTE_EXEC_GROUP } from "@/check/rules/remote-exec";
import { RM_GROUP } from "@/check/rules/rm";

describe("individual rule groups", () => {
  test("RM_GROUP has 1 collapsed rule", () => {
    expect(RM_GROUP.commandRules).toHaveLength(1);
    expect(RM_GROUP.denyGlobs.length).toBeGreaterThan(0);
  });

  test("GIT_PUSH_GROUP has 1 collapsed rule", () => {
    expect(GIT_PUSH_GROUP.commandRules).toHaveLength(1);
  });

  test("GIT_DESTRUCTIVE_GROUP has 4 rules", () => {
    expect(GIT_DESTRUCTIVE_GROUP.commandRules).toHaveLength(4);
  });

  test("GIT_WORKFLOW_GROUP has 2 rules", () => {
    expect(GIT_WORKFLOW_GROUP.commandRules).toHaveLength(2);
  });

  test("CHMOD_GROUP has 2 rules", () => {
    expect(CHMOD_GROUP.commandRules).toHaveLength(2);
  });

  test("REMOTE_EXEC_GROUP has 1 pipe rule", () => {
    expect(REMOTE_EXEC_GROUP.commandRules).toHaveLength(1);
    const rule = REMOTE_EXEC_GROUP.commandRules[0];
    expect(rule?.kind).toBe("pipe");
  });
});

describe("group aggregation", () => {
  test("ALL_RULE_GROUPS contains all 6 groups", () => {
    expect(ALL_RULE_GROUPS).toHaveLength(6);
    const ids = ALL_RULE_GROUPS.map((g) => g.id);
    expect(ids).toContain("rm");
    expect(ids).toContain("git-push");
    expect(ids).toContain("git-destructive");
    expect(ids).toContain("git-workflow");
    expect(ids).toContain("chmod");
    expect(ids).toContain("remote-exec");
  });

  test("collectCommandRules returns 11 rules total", () => {
    const rules = collectCommandRules(ALL_RULE_GROUPS);
    expect(rules).toHaveLength(11);
  });

  test("collectDenyGlobs returns 28 globs total", () => {
    const globs = collectDenyGlobs(ALL_RULE_GROUPS);
    expect(globs).toHaveLength(28);
  });

  test("no duplicate group ids", () => {
    const ids = ALL_RULE_GROUPS.map((g) => g.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
