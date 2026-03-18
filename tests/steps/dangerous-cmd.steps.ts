import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Then, When } from "@questi0nm4rk/feats";
import { DANGEROUS_DENY_GLOBS } from "@/check/rules/groups";
import type { buildRuleSet } from "@/check/ruleset";
import type { CheckDecision, CheckResult } from "@/check/types";
import { isDangerous } from "@/hooks/dangerous-cmd";

// `the default ruleset`, `I evaluate bash command`, `the decision should be/not be`
// are registered once in engine.steps.ts — no duplicates here.

const VALID_DECISIONS = [
  "allow",
  "ask",
  "deny",
] as const satisfies readonly CheckDecision[];

function toCheckDecision(s: string): CheckDecision {
  const found = VALID_DECISIONS.find((d) => d === s);
  if (found !== undefined) {
    return found;
  }
  throw new Error(
    `Invalid decision: "${s}". Expected one of: ${VALID_DECISIONS.join(", ")}`
  );
}

interface HookWorld extends World {
  ruleset?: ReturnType<typeof buildRuleSet>;
  isDangerousResult?: CheckResult | null;
}

When("I run isDangerous with {string}", async (world: HookWorld, command: unknown) => {
  if (typeof command !== "string") throw new Error("expected string");
  world.isDangerousResult = await isDangerous(command);
});

// DocString variant — for commands containing embedded double quotes
When(
  "I run isDangerous with the command",
  async (world: HookWorld, docString: unknown) => {
    if (typeof docString !== "string") throw new Error("expected docstring");
    world.isDangerousResult = await isDangerous(docString.trim());
  }
);

Then("the result should not be null", (world: HookWorld) => {
  expect(world.isDangerousResult).not.toBeNull();
});

Then("the result should be null", (world: HookWorld) => {
  expect(world.isDangerousResult).toBeNull();
});

// isDangerous result check used alongside evaluate result
Then("the isDangerous result should not be null", (world: HookWorld) => {
  expect(world.isDangerousResult).not.toBeNull();
});

Then(
  "the isDangerous result decision should not be {string}",
  (world: HookWorld, decision: unknown) => {
    if (typeof decision !== "string") throw new Error("expected string");
    expect(world.isDangerousResult?.decision).not.toBe(toCheckDecision(decision));
  }
);

Then(
  "DANGEROUS_DENY_GLOBS should contain {string}",
  (_world: HookWorld, entry: unknown) => {
    if (typeof entry !== "string") throw new Error("expected string");
    expect(DANGEROUS_DENY_GLOBS).toContain(entry);
  }
);

Then(
  "DANGEROUS_DENY_GLOBS should not contain {string}",
  (_world: HookWorld, entry: unknown) => {
    if (typeof entry !== "string") throw new Error("expected string");
    expect(DANGEROUS_DENY_GLOBS).not.toContain(entry);
  }
);
