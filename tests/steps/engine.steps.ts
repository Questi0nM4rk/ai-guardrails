import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import { evaluate } from "@/check/engine";
import {
  ALL_RULE_GROUPS,
  COMMAND_RULES,
  collectCommandRules,
  collectDenyGlobs,
  DANGEROUS_DENY_GLOBS,
} from "@/check/rules/groups";
import { DEFAULT_PATH_RULES } from "@/check/rules/paths";
import { buildRuleSet } from "@/check/ruleset";
import type { CheckResult, RuleSet } from "@/check/types";

interface EngineWorld extends World {
  ruleset: RuleSet;
  result: CheckResult;
  rulesList: ReturnType<typeof collectCommandRules>;
  globsList: ReturnType<typeof collectDenyGlobs>;
}

// ─── Given ───────────────────────────────────────────────────────────────────

Given<EngineWorld>("the default ruleset", (world: EngineWorld) => {
  world.ruleset = buildRuleSet({});
});

Given<EngineWorld>("all rule groups", (world: EngineWorld) => {
  world.rulesList = collectCommandRules(ALL_RULE_GROUPS);
  world.globsList = collectDenyGlobs(ALL_RULE_GROUPS);
});

Given<EngineWorld>("the COMMAND_RULES export", (_world: EngineWorld) => {
  // COMMAND_RULES accessed in Then steps directly
});

Given<EngineWorld>("the default path rules", (_world: EngineWorld) => {
  // DEFAULT_PATH_RULES accessed in Then steps directly
});

Given<EngineWorld>("a ruleset built with empty config", (world: EngineWorld) => {
  world.ruleset = buildRuleSet({});
});

Given<EngineWorld>(
  "a ruleset built with managedFiles containing {string}",
  (world: EngineWorld, file: unknown) => {
    world.ruleset = buildRuleSet({ managedFiles: [String(file)] });
  }
);

Given<EngineWorld>(
  "a ruleset built with disabledGroups {string}",
  (world: EngineWorld, group: unknown) => {
    world.ruleset = buildRuleSet({ disabledGroups: [String(group)] });
  }
);

Given<EngineWorld>(
  "a ruleset built with disabledGroups {string} and {string}",
  (world: EngineWorld, g1: unknown, g2: unknown) => {
    world.ruleset = buildRuleSet({ disabledGroups: [String(g1), String(g2)] });
  }
);

Given<EngineWorld>("a ruleset built with all groups disabled", (world: EngineWorld) => {
  world.ruleset = buildRuleSet({
    disabledGroups: ALL_RULE_GROUPS.map((g) => g.id),
  });
});

Given<EngineWorld>(
  "a ruleset built with empty disabledGroups",
  (world: EngineWorld) => {
    world.ruleset = buildRuleSet({ disabledGroups: [] });
  }
);

// ─── When ─────────────────────────────────────────────────────────────────────

When<EngineWorld>(
  "I evaluate bash command {string}",
  async (world: EngineWorld, cmd: unknown) => {
    world.result = await evaluate(
      { type: "bash", command: String(cmd) },
      world.ruleset
    );
  }
);

// DocString variant — for bash commands containing embedded double quotes
When<EngineWorld>(
  "I evaluate bash command with the command",
  async (world: EngineWorld, docString: unknown) => {
    if (typeof docString !== "string") throw new Error("expected docstring");
    const command = docString.trim();
    world.result = await evaluate({ type: "bash", command }, world.ruleset);
  }
);

When<EngineWorld>(
  "I evaluate a write event for path {string}",
  async (world: EngineWorld, path: unknown) => {
    world.result = await evaluate({ type: "write", path: String(path) }, world.ruleset);
  }
);

// Alias used by protect-configs.feature
When<EngineWorld>(
  "I evaluate write to path {string}",
  async (world: EngineWorld, path: unknown) => {
    world.result = await evaluate({ type: "write", path: String(path) }, world.ruleset);
  }
);

When<EngineWorld>(
  "I evaluate a read event for path {string}",
  async (world: EngineWorld, path: unknown) => {
    world.result = await evaluate({ type: "read", path: String(path) }, world.ruleset);
  }
);

// Alias used by protect-reads.feature
When<EngineWorld>(
  "I evaluate read of path {string}",
  async (world: EngineWorld, path: unknown) => {
    world.result = await evaluate({ type: "read", path: String(path) }, world.ruleset);
  }
);

When<EngineWorld>("I collect command rules from no groups", (world: EngineWorld) => {
  world.rulesList = collectCommandRules([]);
});

When<EngineWorld>("I collect deny globs from no groups", (world: EngineWorld) => {
  world.globsList = collectDenyGlobs([]);
});

When<EngineWorld>(
  "I collect command rules from the {string} group only",
  (world: EngineWorld, groupId: unknown) => {
    const group = ALL_RULE_GROUPS.filter((g) => g.id === String(groupId));
    world.rulesList = collectCommandRules(group);
  }
);

// ─── Then ─────────────────────────────────────────────────────────────────────

Then<EngineWorld>(
  "git commit with rm message should be allowed",
  async (world: EngineWorld) => {
    const result = await evaluate(
      { type: "bash", command: 'git commit -m "rm -rf node_modules"' },
      world.ruleset
    );
    expect(result.decision).toBe("allow");
  }
);

Then<EngineWorld>(
  "echo of dangerous string should be allowed",
  async (world: EngineWorld) => {
    const result = await evaluate(
      { type: "bash", command: 'echo "rm -rf /"' },
      world.ruleset
    );
    expect(result.decision).toBe("allow");
  }
);

Then<EngineWorld>(
  "grep for force pattern should be allowed",
  async (world: EngineWorld) => {
    const result = await evaluate(
      { type: "bash", command: 'grep "git push --force" Makefile' },
      world.ruleset
    );
    expect(result.decision).toBe("allow");
  }
);

Then<EngineWorld>(
  "the decision should not be {string}",
  (world: EngineWorld, d: unknown) => {
    expect(String(world.result.decision)).not.toBe(String(d));
  }
);

Then<EngineWorld>(
  "the decision should be {string}",
  (world: EngineWorld, d: unknown) => {
    const decision = String(d);
    if (decision === "not-allow") {
      expect(world.result.decision).not.toBe("allow");
    } else {
      expect(String(world.result.decision)).toBe(decision);
    }
  }
);

Then<EngineWorld>("there should be 6 groups", (_world: EngineWorld) => {
  expect(ALL_RULE_GROUPS).toHaveLength(6);
});

Then<EngineWorld>("each group should have a unique id", (_world: EngineWorld) => {
  const ids = ALL_RULE_GROUPS.map((g) => g.id);
  expect(new Set(ids).size).toBe(ids.length);
});

Then<EngineWorld>(
  "each group should have at least one command rule",
  (_world: EngineWorld) => {
    for (const group of ALL_RULE_GROUPS) {
      expect(group.commandRules.length).toBeGreaterThan(0);
    }
  }
);

Then<EngineWorld>(
  "each group should have at least one deny glob",
  (_world: EngineWorld) => {
    for (const group of ALL_RULE_GROUPS) {
      expect(group.denyGlobs.length).toBeGreaterThan(0);
    }
  }
);

Then<EngineWorld>(
  "the group ids should include {string}",
  (_world: EngineWorld, id: unknown) => {
    const ids = ALL_RULE_GROUPS.map((g) => g.id);
    expect(ids).toContain(String(id));
  }
);

Then<EngineWorld>(
  "collectCommandRules should return all rules from all groups",
  (_world: EngineWorld) => {
    const rules = collectCommandRules(ALL_RULE_GROUPS);
    const total = ALL_RULE_GROUPS.reduce((sum, g) => sum + g.commandRules.length, 0);
    expect(rules).toHaveLength(total);
  }
);

Then<EngineWorld>("the result should be empty", (world: EngineWorld) => {
  if (world.rulesList !== undefined) {
    expect(world.rulesList).toEqual([]);
  } else {
    expect(world.globsList).toEqual([]);
  }
});

Then<EngineWorld>("the result should have 1 rule", (world: EngineWorld) => {
  expect(world.rulesList).toHaveLength(1);
});

Then<EngineWorld>(
  "the first rule should have cmd {string}",
  (world: EngineWorld, cmd: unknown) => {
    const first = world.rulesList[0];
    expect(first).toBeDefined();
    if (first !== undefined && first.kind === "call") {
      expect(first.cmd).toBe(String(cmd));
    }
  }
);

Then<EngineWorld>(
  "collectDenyGlobs should return all globs from all groups",
  (_world: EngineWorld) => {
    const globs = collectDenyGlobs(ALL_RULE_GROUPS);
    const total = ALL_RULE_GROUPS.reduce((sum, g) => sum + g.denyGlobs.length, 0);
    expect(globs).toHaveLength(total);
  }
);

Then<EngineWorld>("it should not contain a recurse rule", (_world: EngineWorld) => {
  expect(COMMAND_RULES.some((r) => r.kind === "recurse")).toBe(false);
});

Then<EngineWorld>(
  "it should contain an rm call rule with --recursive and --force",
  (_world: EngineWorld) => {
    const r = COMMAND_RULES.find(
      (rule) =>
        rule.kind === "call" &&
        rule.cmd === "rm" &&
        rule.flags?.includes("--recursive") &&
        rule.flags?.includes("--force")
    );
    expect(r).toBeDefined();
  }
);

Then<EngineWorld>(
  "DANGEROUS_DENY_GLOBS should equal collectDenyGlobs output",
  (_world: EngineWorld) => {
    expect(DANGEROUS_DENY_GLOBS).toEqual(collectDenyGlobs(ALL_RULE_GROUPS));
  }
);

Then<EngineWorld>(
  "there should be a write rule matching {string}",
  (_world: EngineWorld, path: unknown) => {
    const r = DEFAULT_PATH_RULES.find(
      (rule) => rule.event === "write" && rule.pattern.test(String(path))
    );
    expect(r).toBeDefined();
  }
);

Then<EngineWorld>(
  "there should be a read rule matching {string}",
  (_world: EngineWorld, path: unknown) => {
    const r = DEFAULT_PATH_RULES.find(
      (rule) => rule.event === "read" && rule.pattern.test(String(path))
    );
    expect(r).toBeDefined();
  }
);

Then<EngineWorld>("the ruleset should have command rules", (world: EngineWorld) => {
  expect(world.ruleset.commandRules.length).toBeGreaterThan(0);
});

Then<EngineWorld>("the ruleset should have path rules", (world: EngineWorld) => {
  expect(world.ruleset.pathRules.length).toBeGreaterThan(0);
});

Then<EngineWorld>(
  "the first command rule should be a recurse rule",
  (world: EngineWorld) => {
    expect(world.ruleset.commandRules[0]?.kind).toBe("recurse");
  }
);

Then<EngineWorld>(
  "the path rules should match {string} for write",
  (world: EngineWorld, file: unknown) => {
    const r = world.ruleset.pathRules.find(
      (rule) => rule.event === "write" && rule.pattern.test(String(file))
    );
    expect(r).toBeDefined();
  }
);

Then<EngineWorld>(
  "the command rule count should equal 1 plus the total domain rules",
  (world: EngineWorld) => {
    const totalDomain = collectCommandRules(ALL_RULE_GROUPS).length;
    expect(world.ruleset.commandRules.length).toBe(1 + totalDomain);
  }
);

Then<EngineWorld>(
  "the command rule count should be reduced by the {string} group size",
  (world: EngineWorld, groupId: unknown) => {
    const groupRules =
      ALL_RULE_GROUPS.find((g) => g.id === String(groupId))?.commandRules.length ?? 0;
    const totalDomain = collectCommandRules(ALL_RULE_GROUPS).length;
    expect(world.ruleset.commandRules.length).toBe(1 + totalDomain - groupRules);
  }
);

Then<EngineWorld>(
  "the command rule count should be reduced by those groups combined",
  (world: EngineWorld) => {
    const rmRules =
      ALL_RULE_GROUPS.find((g) => g.id === "destructive-rm")?.commandRules.length ?? 0;
    const chmodRules =
      ALL_RULE_GROUPS.find((g) => g.id === "chmod-world-writable")?.commandRules
        .length ?? 0;
    const totalDomain = collectCommandRules(ALL_RULE_GROUPS).length;
    expect(world.ruleset.commandRules.length).toBe(
      1 + totalDomain - rmRules - chmodRules
    );
  }
);

Then<EngineWorld>("the command rule count should be 1", (world: EngineWorld) => {
  expect(world.ruleset.commandRules.length).toBe(1);
});

Then<EngineWorld>(
  "both rulesets should have the same number of path rules",
  (world: EngineWorld) => {
    const fullRuleset = buildRuleSet({});
    expect(world.ruleset.pathRules.length).toBe(fullRuleset.pathRules.length);
  }
);
