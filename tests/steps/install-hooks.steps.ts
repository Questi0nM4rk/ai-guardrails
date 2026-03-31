import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import type { StepResult } from "@/models/step-result";
import { installHooksStep } from "@/steps/install-hooks";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

const CLAUDE_DIR = "/fake-home/.claude";
const SETTINGS_PATH = `${CLAUDE_DIR}/settings.json`;

interface InstallHooksWorld extends World {
  fm: FakeFileManager;
  cons: FakeConsole;
  stepResult: StepResult;
}

// ── Given steps ──────────────────────────────────────────────────────────────

Given<InstallHooksWorld>("no settings.json exists", (world: InstallHooksWorld) => {
  world.fm = new FakeFileManager();
  world.cons = new FakeConsole();
});

Given<InstallHooksWorld>(
  "settings.json exists with user permissions",
  (world: InstallHooksWorld) => {
    world.fm = new FakeFileManager();
    world.cons = new FakeConsole();
    const existing = {
      permissions: { deny: ["/secret/**"] },
    };
    world.fm.seed(SETTINGS_PATH, JSON.stringify(existing));
  }
);

Given<InstallHooksWorld>(
  "settings.json exists with guardrails hooks",
  async (world: InstallHooksWorld) => {
    const setupFm = new FakeFileManager();
    const setupCons = new FakeConsole();
    // Run once to produce the canonical guardrails output
    await installHooksStep(setupFm, setupCons, CLAUDE_DIR);
    const written = setupFm.written[0];
    if (written === undefined) {
      throw new Error("installHooksStep did not write any file during setup");
    }
    const [, firstContent] = written;

    world.fm = new FakeFileManager();
    world.cons = new FakeConsole();
    world.fm.seed(SETTINGS_PATH, firstContent);
  }
);

Given<InstallHooksWorld>(
  "settings.json contains invalid JSON",
  (world: InstallHooksWorld) => {
    world.fm = new FakeFileManager();
    world.cons = new FakeConsole();
    world.fm.seed(SETTINGS_PATH, "{ invalid json }");
  }
);

// ── When steps ───────────────────────────────────────────────────────────────

When<InstallHooksWorld>("install hooks step runs", async (world: InstallHooksWorld) => {
  world.stepResult = await installHooksStep(world.fm, world.cons, CLAUDE_DIR);
});

// ── Then steps ────────────────────────────────────────────────────────────────

Then<InstallHooksWorld>(
  "settings.json should be created",
  (world: InstallHooksWorld) => {
    const written = world.fm.written.map(([p]) => p);
    expect(written).toContain(SETTINGS_PATH);
  }
);

Then<InstallHooksWorld>(
  "it should contain PreToolUse hooks",
  (world: InstallHooksWorld) => {
    const entry = world.fm.written.find(([p]) => p === SETTINGS_PATH);
    expect(entry).toBeDefined();
    const [, content] = entry ?? ["", ""];
    const parsed = JSON.parse(content) as Record<string, unknown>;
    const hooks = parsed.hooks as Record<string, unknown> | undefined;
    expect(hooks?.PreToolUse).toBeDefined();
  }
);

Then<InstallHooksWorld>(
  "the existing permissions should be preserved",
  (world: InstallHooksWorld) => {
    const entry = world.fm.written.find(([p]) => p === SETTINGS_PATH);
    expect(entry).toBeDefined();
    const [, content] = entry ?? ["", ""];
    const parsed = JSON.parse(content) as Record<string, unknown>;
    const permissions = parsed.permissions as { deny?: string[] } | undefined;
    expect(permissions?.deny).toEqual(["/secret/**"]);
  }
);

Then<InstallHooksWorld>(
  "PreToolUse hooks should be added",
  (world: InstallHooksWorld) => {
    const entry = world.fm.written.find(([p]) => p === SETTINGS_PATH);
    expect(entry).toBeDefined();
    const [, content] = entry ?? ["", ""];
    const parsed = JSON.parse(content) as Record<string, unknown>;
    const hooks = parsed.hooks as Record<string, unknown> | undefined;
    const ptus = hooks?.PreToolUse as Array<{ matcher: string }> | undefined;
    expect(ptus).toBeDefined();
    expect((ptus ?? []).length).toBeGreaterThan(0);
  }
);

Then<InstallHooksWorld>(
  "PreToolUse hooks should not be duplicated",
  (world: InstallHooksWorld) => {
    const entry = world.fm.written.find(([p]) => p === SETTINGS_PATH);
    expect(entry).toBeDefined();
    const [, content] = entry ?? ["", ""];
    const parsed = JSON.parse(content) as Record<string, unknown>;
    const hooks = parsed.hooks as Record<string, unknown> | undefined;
    const ptus = hooks?.PreToolUse as
      | Array<{ matcher: string; hooks: unknown[] }>
      | undefined;
    expect(ptus).toBeDefined();
    const matchers = (ptus ?? []).map((e) => e.matcher);
    const uniqueMatchers = new Set(matchers);
    expect(uniqueMatchers.size).toBe(matchers.length);
    // Also verify hook commands are not duplicated within each matcher
    for (const entry of ptus ?? []) {
      const commands = entry.hooks.map((h) => (h as { command: string }).command);
      const uniqueCommands = new Set(commands);
      expect(uniqueCommands.size).toBe(commands.length);
    }
  }
);

Then<InstallHooksWorld>(
  "hooks should include matcher {string}",
  (world: InstallHooksWorld, matcher: unknown) => {
    const entry = world.fm.written.find(([p]) => p === SETTINGS_PATH);
    expect(entry).toBeDefined();
    const [, content] = entry ?? ["", ""];
    const parsed = JSON.parse(content) as Record<string, unknown>;
    const hooks = parsed.hooks as Record<string, unknown> | undefined;
    const ptus = hooks?.PreToolUse as Array<{ matcher: string }> | undefined;
    expect((ptus ?? []).some((e) => e.matcher === String(matcher))).toBe(true);
  }
);

Then<InstallHooksWorld>(
  "all hook commands should contain {string}",
  (world: InstallHooksWorld, guard: unknown) => {
    const entry = world.fm.written.find(([p]) => p === SETTINGS_PATH);
    expect(entry).toBeDefined();
    const [, content] = entry ?? ["", ""];
    const parsed = JSON.parse(content) as Record<string, unknown>;
    const hooks = parsed.hooks as Record<string, unknown> | undefined;
    const ptus =
      (hooks?.PreToolUse as Array<{ hooks: Array<{ command: string }> }>) ?? [];
    for (const ptu of ptus) {
      for (const hook of ptu.hooks) {
        expect(hook.command).toContain(String(guard));
      }
    }
  }
);

Then<InstallHooksWorld>("the step should succeed", (world: InstallHooksWorld) => {
  expect(world.stepResult.status).toBe("ok");
});

Then<InstallHooksWorld>(
  "settings.json should contain valid hooks",
  (world: InstallHooksWorld) => {
    const entry = world.fm.written.find(([p]) => p === SETTINGS_PATH);
    expect(entry).toBeDefined();
    const [, content] = entry ?? ["", ""];
    // Must parse as valid JSON
    const parsed = JSON.parse(content) as Record<string, unknown>;
    const hooks = parsed.hooks as Record<string, unknown> | undefined;
    const ptus = hooks?.PreToolUse as Array<{ matcher: string }> | undefined;
    expect((ptus ?? []).length).toBeGreaterThan(0);
  }
);
