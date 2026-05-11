import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import type { CheckResult, ToolEvent } from "@/check/in-process";
import { evaluateInProcess } from "@/check/in-process";
import {
  ALL_RULE_GROUPS,
  collectDenyGlobs,
  DANGEROUS_DENY_GLOBS,
} from "@/check/rules/groups";

// Test world. ruleset/config drive evaluation; counters cover collection helpers.
interface EngineWorld extends World {
  config: { disabledGroups?: string[]; managedFiles?: string[] };
  result: CheckResult;
  globsList: string[];
  groupCount: number;
}

async function evalIn(event: ToolEvent, world: EngineWorld): Promise<CheckResult> {
  // The in-process helper uses cwd's config.toml; for tests we override by
  // building modules directly when config is set. Otherwise default config
  // applies (which is what the BDD scenarios assume by default).
  if (
    (world.config?.disabledGroups?.length ?? 0) === 0 &&
    (world.config?.managedFiles?.length ?? 0) === 0
  ) {
    return await evaluateInProcess(event);
  }
  // Build modules with explicit config — bypass the cwd-config loader.
  const { evaluate } = await import("@questi0nm4rk/hook-kit");
  const { buildAllModules } = await import("@/check/ruleset");
  const { synthesizeEvent } = await import("@/check/in-process");
  const modules = buildAllModules(world.config);
  const decision = await evaluate(synthesizeEvent(event, "ag-test"), modules);
  if (decision === null) return { decision: "allow" };
  if (decision.kind === "deny") return { decision: "deny", reason: decision.reason };
  if (decision.kind === "escalate") return { decision: "ask", reason: decision.reason };
  return { decision: "allow" };
}

// ─── Given ───────────────────────────────────────────────────────────────────

Given<EngineWorld>("the default ruleset", (world: EngineWorld) => {
  world.config = {};
});

Given<EngineWorld>("all rule groups", (world: EngineWorld) => {
  world.groupCount = ALL_RULE_GROUPS.length;
  world.globsList = collectDenyGlobs(ALL_RULE_GROUPS);
});

Given<EngineWorld>("a ruleset built with empty config", (world: EngineWorld) => {
  world.config = {};
});

Given<EngineWorld>(
  "a ruleset built with managedFiles containing {string}",
  (world: EngineWorld, file: unknown) => {
    world.config = { managedFiles: [String(file)] };
  }
);

Given<EngineWorld>(
  "a ruleset built with disabledGroups {string}",
  (world: EngineWorld, group: unknown) => {
    world.config = { disabledGroups: [String(group)] };
  }
);

Given<EngineWorld>(
  "a ruleset built with disabledGroups {string} and {string}",
  (world: EngineWorld, g1: unknown, g2: unknown) => {
    world.config = { disabledGroups: [String(g1), String(g2)] };
  }
);

Given<EngineWorld>("a ruleset built with all groups disabled", (world: EngineWorld) => {
  world.config = { disabledGroups: ALL_RULE_GROUPS.map((g) => g.id) };
});

Given<EngineWorld>(
  "a ruleset built with empty disabledGroups",
  (world: EngineWorld) => {
    world.config = { disabledGroups: [] };
  }
);

// ─── When ─────────────────────────────────────────────────────────────────────

When<EngineWorld>(
  "I evaluate bash command {string}",
  async (world: EngineWorld, cmd: unknown) => {
    world.result = await evalIn({ type: "bash", command: String(cmd) }, world);
  }
);

When<EngineWorld>(
  "I evaluate bash command with the command",
  async (world: EngineWorld, docString: unknown) => {
    if (typeof docString !== "string") throw new Error("expected docstring");
    world.result = await evalIn({ type: "bash", command: docString.trim() }, world);
  }
);

When<EngineWorld>(
  "I evaluate a write event for path {string}",
  async (world: EngineWorld, p: unknown) => {
    world.result = await evalIn({ type: "write", path: String(p) }, world);
  }
);

When<EngineWorld>(
  "I evaluate write to path {string}",
  async (world: EngineWorld, p: unknown) => {
    world.result = await evalIn({ type: "write", path: String(p) }, world);
  }
);

When<EngineWorld>(
  "I evaluate a read event for path {string}",
  async (world: EngineWorld, p: unknown) => {
    world.result = await evalIn({ type: "read", path: String(p) }, world);
  }
);

When<EngineWorld>(
  "I evaluate read of path {string}",
  async (world: EngineWorld, p: unknown) => {
    world.result = await evalIn({ type: "read", path: String(p) }, world);
  }
);

// ─── Then ─────────────────────────────────────────────────────────────────────

Then<EngineWorld>(
  "git commit with rm message should be allowed",
  async (world: EngineWorld) => {
    const r = await evalIn(
      { type: "bash", command: 'git commit -m "rm -rf node_modules"' },
      world
    );
    expect(r.decision).toBe("allow");
  }
);

Then<EngineWorld>(
  "echo of dangerous string should be allowed",
  async (world: EngineWorld) => {
    const r = await evalIn({ type: "bash", command: 'echo "rm -rf /"' }, world);
    expect(r.decision).toBe("allow");
  }
);

Then<EngineWorld>(
  "grep for force pattern should be allowed",
  async (world: EngineWorld) => {
    const r = await evalIn(
      { type: "bash", command: 'grep "git push --force" Makefile' },
      world
    );
    expect(r.decision).toBe("allow");
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

// Group-structure assertions — preserved against the new shape
Then<EngineWorld>("there should be 6 groups", () => {
  expect(ALL_RULE_GROUPS).toHaveLength(6);
});

Then<EngineWorld>("each group should have a unique id", () => {
  const ids = ALL_RULE_GROUPS.map((g) => g.id);
  expect(new Set(ids).size).toBe(ids.length);
});

Then<EngineWorld>("each group should have at least one deny glob", () => {
  for (const g of ALL_RULE_GROUPS) {
    expect(g.denyGlobs.length).toBeGreaterThan(0);
  }
});

Then<EngineWorld>(
  "the group ids should include {string}",
  (_world: EngineWorld, id: unknown) => {
    expect(ALL_RULE_GROUPS.map((g) => g.id)).toContain(String(id));
  }
);

Then<EngineWorld>("DANGEROUS_DENY_GLOBS should equal collectDenyGlobs output", () => {
  expect(DANGEROUS_DENY_GLOBS).toEqual(collectDenyGlobs(ALL_RULE_GROUPS));
});
