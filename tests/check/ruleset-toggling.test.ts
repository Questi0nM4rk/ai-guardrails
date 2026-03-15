import { describe, expect, test } from "bun:test";
import { buildRuleSet } from "@/check/ruleset";

describe("buildRuleSet with disabledGroups", () => {
  test("empty config returns all rules (1 recurse + 11 domain)", () => {
    const rs = buildRuleSet({});
    expect(rs.commandRules.length).toBe(12);
    expect(rs.commandRules[0]?.kind).toBe("recurse");
  });

  test("disabling destructive-rm removes 1 rule", () => {
    const rs = buildRuleSet({ disabledGroups: ["destructive-rm"] });
    expect(rs.commandRules.length).toBe(11);
  });

  test("disabling destructive-rm and chmod-world-writable removes 3 rules", () => {
    const rs = buildRuleSet({
      disabledGroups: ["destructive-rm", "chmod-world-writable"],
    });
    expect(rs.commandRules.length).toBe(9);
  });

  test("recurse rule always present regardless of disabled groups", () => {
    const rs = buildRuleSet({
      disabledGroups: [
        "destructive-rm",
        "git-force-push",
        "git-destructive",
        "git-bypass-hooks",
        "chmod-world-writable",
        "remote-code-exec",
      ],
    });
    expect(rs.commandRules.length).toBe(1);
    expect(rs.commandRules[0]?.kind).toBe("recurse");
  });

  test("unknown group names are silently ignored", () => {
    const rs = buildRuleSet({ disabledGroups: ["nonexistent"] });
    expect(rs.commandRules.length).toBe(12);
  });

  test("empty disabledGroups array enables all groups", () => {
    const rs = buildRuleSet({ disabledGroups: [] });
    expect(rs.commandRules.length).toBe(12);
  });

  test("path rules unaffected by disabledGroups", () => {
    const full = buildRuleSet({});
    const partial = buildRuleSet({ disabledGroups: ["destructive-rm"] });
    expect(partial.pathRules.length).toBe(full.pathRules.length);
  });
});
