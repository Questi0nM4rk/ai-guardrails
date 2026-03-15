import { describe, expect, test } from "bun:test";
import { ALL_RULE_GROUPS, collectCommandRules } from "@/check/rules/groups";
import { buildRuleSet } from "@/check/ruleset";

const totalDomainRules = collectCommandRules(ALL_RULE_GROUPS).length;

describe("buildRuleSet with disabledGroups", () => {
  test("empty config returns all rules (1 recurse + domain rules)", () => {
    const rs = buildRuleSet({});
    expect(rs.commandRules.length).toBe(1 + totalDomainRules);
    expect(rs.commandRules[0]?.kind).toBe("recurse");
  });

  test("disabling destructive-rm removes its rules", () => {
    const rmRules =
      ALL_RULE_GROUPS.find((g) => g.id === "destructive-rm")?.commandRules.length ?? 0;
    const rs = buildRuleSet({ disabledGroups: ["destructive-rm"] });
    expect(rs.commandRules.length).toBe(1 + totalDomainRules - rmRules);
  });

  test("disabling multiple groups removes their rules", () => {
    const rmRules =
      ALL_RULE_GROUPS.find((g) => g.id === "destructive-rm")?.commandRules.length ?? 0;
    const chmodRules =
      ALL_RULE_GROUPS.find((g) => g.id === "chmod-world-writable")?.commandRules
        .length ?? 0;
    const rs = buildRuleSet({
      disabledGroups: ["destructive-rm", "chmod-world-writable"],
    });
    expect(rs.commandRules.length).toBe(1 + totalDomainRules - rmRules - chmodRules);
  });

  test("recurse rule always present regardless of disabled groups", () => {
    const rs = buildRuleSet({
      disabledGroups: ALL_RULE_GROUPS.map((g) => g.id),
    });
    expect(rs.commandRules.length).toBe(1);
    expect(rs.commandRules[0]?.kind).toBe("recurse");
  });

  test("unknown group names log warning but don't break", () => {
    const rs = buildRuleSet({ disabledGroups: ["nonexistent"] });
    expect(rs.commandRules.length).toBe(1 + totalDomainRules);
  });

  test("empty disabledGroups array enables all groups", () => {
    const rs = buildRuleSet({ disabledGroups: [] });
    expect(rs.commandRules.length).toBe(1 + totalDomainRules);
  });

  test("path rules unaffected by disabledGroups", () => {
    const full = buildRuleSet({});
    const partial = buildRuleSet({ disabledGroups: ["destructive-rm"] });
    expect(partial.pathRules.length).toBe(full.pathRules.length);
  });
});
