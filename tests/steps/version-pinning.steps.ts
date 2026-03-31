import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { versionPinModule } from "@/init/modules/version-pin";
import type { InitContext } from "@/init/types";
import { PROJECT_CONFIG_PATH } from "@/models/paths";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";
const CONFIG_PATH = `${PROJECT_DIR}/${PROJECT_CONFIG_PATH}`;

interface VersionPinWorld extends World {
  fm: FakeFileManager;
  console: FakeConsole;
  configContent: string;
}

function makeInitCtx(
  fm: FakeFileManager,
  cons: FakeConsole,
  flags: Record<string, unknown> = {}
): InitContext {
  return {
    projectDir: PROJECT_DIR,
    fileManager: fm,
    commandRunner: new FakeCommandRunner(),
    console: cons,
    config: buildResolvedConfig(
      MachineConfigSchema.parse({}),
      ProjectConfigSchema.parse({})
    ),
    languages: [],
    selections: new Map(),
    isTTY: false,
    createReadline: () => {
      throw new Error("readline not available in test");
    },
    flags,
  };
}

Given<VersionPinWorld>(
  "a project for version pin testing",
  (world: VersionPinWorld) => {
    world.fm = new FakeFileManager();
    world.console = new FakeConsole();
  }
);

Given<VersionPinWorld>(
  "a project pinned to version {string}",
  (world: VersionPinWorld, version: unknown) => {
    world.fm = new FakeFileManager();
    world.console = new FakeConsole();
    world.fm.seed(CONFIG_PATH, `min_version = "${String(version)}"\n`);
  }
);

When<VersionPinWorld>(
  "init runs with version pinning enabled",
  async (world: VersionPinWorld) => {
    const ctx = makeInitCtx(world.fm, world.console);
    await versionPinModule.execute(ctx);
    try {
      world.configContent = await world.fm.readText(CONFIG_PATH);
    } catch {
      world.configContent = "";
    }
  }
);

When<VersionPinWorld>("version status is checked", async (world: VersionPinWorld) => {
  const ctx = makeInitCtx(world.fm, world.console);
  await versionPinModule.execute(ctx);
  try {
    world.configContent = await world.fm.readText(CONFIG_PATH);
  } catch {
    world.configContent = "";
  }
});

When<VersionPinWorld>(
  "init runs with --min-version {string}",
  async (world: VersionPinWorld, minVersion: unknown) => {
    const ctx = makeInitCtx(world.fm, world.console, {
      minVersion: String(minVersion),
    });
    await versionPinModule.execute(ctx);
    try {
      world.configContent = await world.fm.readText(CONFIG_PATH);
    } catch {
      world.configContent = "";
    }
  }
);

Then<VersionPinWorld>(
  "config.toml should contain {string}",
  (world: VersionPinWorld, text: unknown) => {
    expect(world.configContent).toContain(String(text));
  }
);

Then<VersionPinWorld>(
  "a version mismatch warning should be emitted",
  (world: VersionPinWorld) => {
    expect(world.console.warnings.length).toBeGreaterThan(0);
    expect(world.console.warnings.join("\n")).toContain("Version pin preserved");
  }
);

Then<VersionPinWorld>(
  "no version mismatch warning should be emitted",
  (world: VersionPinWorld) => {
    const hasVersionWarning = world.console.warnings.some((w) =>
      w.includes("Version pin preserved")
    );
    expect(hasVersionWarning).toBe(false);
  }
);
