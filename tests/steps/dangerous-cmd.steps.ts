import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import { evaluate } from "@/check/engine";
import { DANGEROUS_DENY_GLOBS } from "@/check/rules/groups";
import { buildRuleSet } from "@/check/ruleset";
import type { CheckDecision, CheckResult } from "@/check/types";
import { isDangerous } from "@/hooks/dangerous-cmd";

const VALID_DECISIONS = ["allow", "ask", "deny"] as const;

function toCheckDecision(s: string): CheckDecision {
  if ((VALID_DECISIONS as readonly string[]).includes(s)) {
    return s as CheckDecision;
  }
  throw new Error(
    `Invalid decision: "${s}". Expected one of: ${VALID_DECISIONS.join(", ")}`
  );
}

interface HookWorld extends World {
  ruleset: ReturnType<typeof buildRuleSet>;
  isDangerousResult: CheckResult | null;
  evaluateResult: CheckResult;
}

Given("the default ruleset", (world: HookWorld) => {
  world.ruleset = buildRuleSet({});
});

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

When("I evaluate bash command {string}", async (world: HookWorld, command: unknown) => {
  if (typeof command !== "string") throw new Error("expected string");
  world.evaluateResult = await evaluate({ type: "bash", command }, world.ruleset);
});

// DocString variant — for bash commands containing embedded double quotes
When(
  "I evaluate bash command with the command",
  async (world: HookWorld, docString: unknown) => {
    if (typeof docString !== "string") throw new Error("expected docstring");
    const command = docString.trim();
    world.evaluateResult = await evaluate({ type: "bash", command }, world.ruleset);
  }
);

When("I evaluate write to path {string}", async (world: HookWorld, path: unknown) => {
  if (typeof path !== "string") throw new Error("expected string");
  world.evaluateResult = await evaluate({ type: "write", path }, world.ruleset);
});

When("I evaluate read of path {string}", async (world: HookWorld, path: unknown) => {
  if (typeof path !== "string") throw new Error("expected string");
  world.evaluateResult = await evaluate({ type: "read", path }, world.ruleset);
});

Then("the decision should be {string}", (world: HookWorld, decision: unknown) => {
  if (typeof decision !== "string") throw new Error("expected string");
  expect(world.evaluateResult.decision).toBe(toCheckDecision(decision));
});

Then("the decision should not be {string}", (world: HookWorld, decision: unknown) => {
  if (typeof decision !== "string") throw new Error("expected string");
  expect(world.evaluateResult.decision).not.toBe(toCheckDecision(decision));
});

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
