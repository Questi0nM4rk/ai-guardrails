import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import type { NoConsoleLevel } from "@/utils/detect-project-type";
import { detectNoConsoleLevel } from "@/utils/detect-project-type";

interface NoConsoleWorld extends World {
  packageJsonInput: unknown;
  detectedLevel: NoConsoleLevel;
}

// ─── Given steps ──────────────────────────────────────────────────────────────

Given<NoConsoleWorld>(
  "a package.json with bin field as string",
  (world: NoConsoleWorld) => {
    world.packageJsonInput = { bin: "./cli.js" };
  }
);

Given<NoConsoleWorld>(
  "a package.json with bin field as object",
  (world: NoConsoleWorld) => {
    world.packageJsonInput = { bin: { mytool: "./cli.js" } };
  }
);

Given<NoConsoleWorld>(
  "a package.json with dependency {string}",
  (world: NoConsoleWorld, dep: unknown) => {
    world.packageJsonInput = { dependencies: { [String(dep)]: "^1.0.0" } };
  }
);

Given<NoConsoleWorld>(
  "a package.json with devDependency {string}",
  (world: NoConsoleWorld, dep: unknown) => {
    world.packageJsonInput = { devDependencies: { [String(dep)]: "^1.0.0" } };
  }
);

Given<NoConsoleWorld>(
  "a package.json with bin and dependency {string}",
  (world: NoConsoleWorld, dep: unknown) => {
    world.packageJsonInput = {
      bin: "./cli.js",
      dependencies: { [String(dep)]: "^1.0.0" },
    };
  }
);

Given<NoConsoleWorld>("a minimal package.json", (world: NoConsoleWorld) => {
  world.packageJsonInput = {};
});

Given<NoConsoleWorld>("no package.json content", (world: NoConsoleWorld) => {
  world.packageJsonInput = null;
});

Given<NoConsoleWorld>(
  "a non-object package.json with value {int}",
  (world: NoConsoleWorld, value: unknown) => {
    world.packageJsonInput = Number(value);
  }
);

Given<NoConsoleWorld>(
  "a non-object package.json with value {string}",
  (world: NoConsoleWorld, value: unknown) => {
    world.packageJsonInput = String(value);
  }
);

// ─── When ─────────────────────────────────────────────────────────────────────

When<NoConsoleWorld>("noConsole level is detected", (world: NoConsoleWorld) => {
  world.detectedLevel = detectNoConsoleLevel(world.packageJsonInput);
});

// ─── Then ─────────────────────────────────────────────────────────────────────

Then<NoConsoleWorld>(
  "the noConsole level should be {string}",
  (world: NoConsoleWorld, level: unknown) => {
    const s = String(level);
    expect(["off", "warn", "error"]).toContain(s);
    const expected: NoConsoleLevel =
      s === "off" ? "off" : s === "error" ? "error" : "warn";
    expect(world.detectedLevel).toBe(expected);
  }
);
