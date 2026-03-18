import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import type { MachineConfig, ProjectConfig, ResolvedConfig } from "@/config/loader";
import { loadMachineConfig, loadProjectConfig, resolveConfig } from "@/config/loader";
import { PROFILES } from "@/config/schema";
import { FakeFileManager } from "../fakes/fake-file-manager";

function toProfile(value: string): MachineConfig["profile"] {
  const found = PROFILES.find((p) => p === value);
  if (found !== undefined) {
    return found;
  }
  throw new Error(
    `Invalid profile: "${value}". Expected one of: ${PROFILES.join(", ")}`
  );
}

interface ConfigWorld extends World {
  fm: FakeFileManager;
  machineConfig: MachineConfig;
  projectConfig: ProjectConfig;
  resolvedConfig: ResolvedConfig;
  loadError: unknown;
  machineForResolve: MachineConfig;
  projectForResolve: ProjectConfig;
  projectDir: string;
}

// ─── Given ───────────────────────────────────────────────────────────────────

Given<ConfigWorld>(
  "a file at {string} containing {string}",
  (world: ConfigWorld, path: unknown, content: unknown) => {
    if (world.fm === undefined) {
      world.fm = new FakeFileManager();
    }
    world.fm.seed(String(path), String(content));
  }
);

// Step used with Gherkin docstring — trailing colon is included in step text by the parser
Given<ConfigWorld>(
  "a file at {string} containing:",
  (world: ConfigWorld, path: unknown, docString: unknown) => {
    if (world.fm === undefined) {
      world.fm = new FakeFileManager();
    }
    world.fm.seed(String(path), String(docString));
  }
);

Given<ConfigWorld>("no file at {string}", (world: ConfigWorld, _path: unknown) => {
  if (world.fm === undefined) {
    world.fm = new FakeFileManager();
  }
  // No seeding — file absent
});

Given<ConfigWorld>(
  "a machine config with profile {string}",
  (world: ConfigWorld, profile: unknown) => {
    world.machineForResolve = {
      profile: toProfile(String(profile)),
      ignore: [],
    };
  }
);

Given<ConfigWorld>(
  "a project config with profile {string}",
  (world: ConfigWorld, profile: unknown) => {
    world.projectForResolve = {
      profile: toProfile(String(profile)),
      config: { line_length: 88, indent_width: 2 },
      ignore: [],
      allow: [],
      ignore_paths: [],
    };
  }
);

Given<ConfigWorld>("a project config with no profile", (world: ConfigWorld) => {
  world.projectForResolve = {
    config: { line_length: 88, indent_width: 2 },
    ignore: [],
    allow: [],
    ignore_paths: [],
  };
});

Given<ConfigWorld>(
  "a machine config ignoring {string} with reason {string}",
  (world: ConfigWorld, rule: unknown, reason: unknown) => {
    world.machineForResolve = {
      profile: "standard",
      ignore: [{ rule: String(rule), reason: String(reason) }],
    };
  }
);

Given<ConfigWorld>(
  "a project config ignoring {string} with reason {string}",
  (world: ConfigWorld, rule: unknown, reason: unknown) => {
    world.projectForResolve = {
      config: { line_length: 88, indent_width: 2 },
      ignore: [{ rule: String(rule), reason: String(reason) }],
      allow: [],
      ignore_paths: [],
    };
  }
);

Given<ConfigWorld>(
  "a machine config ignoring {string}",
  (world: ConfigWorld, rule: unknown) => {
    world.machineForResolve = {
      profile: "standard",
      ignore: [{ rule: String(rule), reason: "test" }],
    };
  }
);

Given<ConfigWorld>(
  "a project config ignoring {string}",
  (world: ConfigWorld, rule: unknown) => {
    world.projectForResolve = {
      config: { line_length: 88, indent_width: 2 },
      ignore: [{ rule: String(rule), reason: "test" }],
      allow: [],
      ignore_paths: [],
    };
  }
);

Given<ConfigWorld>(
  "a resolved config ignoring {string}",
  (world: ConfigWorld, rule: unknown) => {
    const machine: MachineConfig = {
      profile: "standard",
      ignore: [{ rule: String(rule), reason: "test" }],
    };
    const project: ProjectConfig = {
      config: { line_length: 88, indent_width: 2 },
      ignore: [],
      allow: [],
      ignore_paths: [],
    };
    world.resolvedConfig = resolveConfig(machine, project);
  }
);

Given<ConfigWorld>("a resolved config with no ignores", (world: ConfigWorld) => {
  const machine: MachineConfig = { profile: "standard", ignore: [] };
  const project: ProjectConfig = {
    config: { line_length: 88, indent_width: 2 },
    ignore: [],
    allow: [],
    ignore_paths: [],
  };
  world.resolvedConfig = resolveConfig(machine, project);
});

Given<ConfigWorld>(
  "a resolved config allowing {string} for glob {string}",
  (world: ConfigWorld, rule: unknown, glob: unknown) => {
    const machine: MachineConfig = { profile: "standard", ignore: [] };
    const project: ProjectConfig = {
      config: { line_length: 88, indent_width: 2 },
      ignore: [],
      allow: [{ rule: String(rule), glob: String(glob), reason: "test" }],
      ignore_paths: [],
    };
    world.resolvedConfig = resolveConfig(machine, project);
  }
);

// ─── When ─────────────────────────────────────────────────────────────────────

When<ConfigWorld>(
  "I load the machine config from {string}",
  async (world: ConfigWorld, path: unknown) => {
    try {
      world.machineConfig = await loadMachineConfig(
        String(path),
        world.fm ?? new FakeFileManager()
      );
    } catch (e: unknown) {
      world.loadError = e;
    }
  }
);

When<ConfigWorld>(
  "I load the project config from {string}",
  async (world: ConfigWorld, dir: unknown) => {
    try {
      world.projectConfig = await loadProjectConfig(
        String(dir),
        world.fm ?? new FakeFileManager()
      );
    } catch (e: unknown) {
      world.loadError = e;
    }
  }
);

When<ConfigWorld>("I resolve the config", (world: ConfigWorld) => {
  const machine = world.machineForResolve ?? {
    profile: "standard" as const,
    ignore: [],
  };
  const project = world.projectForResolve ?? {
    config: { line_length: 88, indent_width: 2 },
    ignore: [],
    allow: [],
    ignore_paths: [],
  };
  world.resolvedConfig = resolveConfig(machine, project);
});

// ─── Then ─────────────────────────────────────────────────────────────────────

Then<ConfigWorld>(
  "the profile should be {string}",
  (world: ConfigWorld, profile: unknown) => {
    const p = String(profile);
    if (world.machineConfig !== undefined) {
      expect(String(world.machineConfig.profile)).toBe(p);
    } else if (world.projectConfig !== undefined) {
      expect(String(world.projectConfig.profile)).toBe(p);
    } else {
      throw new Error(
        "No config loaded — set world.machineConfig or world.projectConfig first"
      );
    }
  }
);

Then<ConfigWorld>("the profile should be undefined", (world: ConfigWorld) => {
  expect(world.projectConfig.profile).toBeUndefined();
});

Then<ConfigWorld>(
  "the ignore list should have {int} entry",
  (world: ConfigWorld, count: unknown) => {
    const n = Number(count);
    if (world.machineConfig !== undefined) {
      expect(world.machineConfig.ignore).toHaveLength(n);
    } else if (world.projectConfig !== undefined) {
      expect(world.projectConfig.ignore).toHaveLength(n);
    }
  }
);

Then<ConfigWorld>("the ignore list should be empty", (world: ConfigWorld) => {
  if (world.machineConfig !== undefined) {
    expect(world.machineConfig.ignore).toEqual([]);
  } else if (world.projectConfig !== undefined) {
    expect(world.projectConfig.ignore).toEqual([]);
  }
});

Then<ConfigWorld>(
  "the first ignore rule should be {string}",
  (world: ConfigWorld, rule: unknown) => {
    if (world.machineConfig !== undefined) {
      expect(world.machineConfig.ignore[0]?.rule).toBe(String(rule));
    }
  }
);

Then<ConfigWorld>(
  "the config line_length should be {int}",
  (world: ConfigWorld, value: unknown) => {
    expect(world.projectConfig.config.line_length).toBe(Number(value));
  }
);

Then<ConfigWorld>("it should throw an error", (world: ConfigWorld) => {
  expect(world.loadError).toBeDefined();
});

Then<ConfigWorld>(
  "the resolved profile should be {string}",
  (world: ConfigWorld, profile: unknown) => {
    expect(String(world.resolvedConfig.profile)).toBe(String(profile));
  }
);

Then<ConfigWorld>(
  "the resolved ignore list should have {int} entries",
  (world: ConfigWorld, count: unknown) => {
    expect(world.resolvedConfig.ignore).toHaveLength(Number(count));
  }
);

Then<ConfigWorld>(
  "the resolved ignore list should contain {string}",
  (world: ConfigWorld, rule: unknown) => {
    const rules = world.resolvedConfig.ignore.map((i) => i.rule);
    expect(rules).toContain(String(rule));
  }
);

Then<ConfigWorld>(
  "the resolved ignore list should have 1 entry",
  (world: ConfigWorld) => {
    expect(world.resolvedConfig.ignore).toHaveLength(1);
  }
);

Then<ConfigWorld>(
  "the first ignore entry reason should be {string}",
  (world: ConfigWorld, reason: unknown) => {
    expect(world.resolvedConfig.ignore[0]?.reason).toBe(String(reason));
  }
);

Then<ConfigWorld>(
  "isAllowed for rule {string} on path {string} should be true",
  (world: ConfigWorld, rule: unknown, path: unknown) => {
    expect(world.resolvedConfig.isAllowed(String(rule), String(path))).toBe(true);
  }
);

Then<ConfigWorld>(
  "isAllowed for rule {string} on path {string} should be false",
  (world: ConfigWorld, rule: unknown, path: unknown) => {
    expect(world.resolvedConfig.isAllowed(String(rule), String(path))).toBe(false);
  }
);

Then<ConfigWorld>(
  "ignoredRules should contain {string}",
  (world: ConfigWorld, rule: unknown) => {
    expect(world.resolvedConfig.ignoredRules.has(String(rule))).toBe(true);
  }
);

Then<ConfigWorld>(
  "ignoredRules should not contain {string}",
  (world: ConfigWorld, rule: unknown) => {
    expect(world.resolvedConfig.ignoredRules.has(String(rule))).toBe(false);
  }
);
