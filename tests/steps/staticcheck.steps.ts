import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { staticcheckGenerator } from "@/generators/staticcheck";
import { staticcheckConfigModule } from "@/init/modules/staticcheck-config";
import type { InitContext } from "@/init/types";
import type { LanguagePlugin } from "@/languages/types";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";

interface StaticcheckWorld extends World {
  fm: FakeFileManager;
  generatedContent: string;
  detected: boolean;
}

function makeLanguagePlugin(id: string): LanguagePlugin {
  return {
    id,
    name: id,
    detect: async () => true,
    runners: () => [],
  };
}

function makeInitCtx(
  fm: FakeFileManager,
  languages: LanguagePlugin[],
  flags: Record<string, unknown> = {}
): InitContext {
  return {
    projectDir: PROJECT_DIR,
    fileManager: fm,
    commandRunner: new FakeCommandRunner(),
    console: new FakeConsole(),
    config: buildResolvedConfig(
      MachineConfigSchema.parse({}),
      ProjectConfigSchema.parse({})
    ),
    languages,
    selections: new Map(),
    isTTY: false,
    createReadline: () => {
      throw new Error("readline not available in test");
    },
    flags,
  };
}

Given<StaticcheckWorld>(
  "a Go project for staticcheck testing",
  (world: StaticcheckWorld) => {
    world.fm = new FakeFileManager();
    world.fm.seed(`${PROJECT_DIR}/main.go`, "package main\n");
  }
);

Given<StaticcheckWorld>(
  "a TypeScript project for staticcheck testing",
  (world: StaticcheckWorld) => {
    world.fm = new FakeFileManager();
    world.fm.seed(`${PROJECT_DIR}/index.ts`, "export const x = 1;\n");
  }
);

When<StaticcheckWorld>(
  "the staticcheck config is generated",
  async (world: StaticcheckWorld) => {
    const config = buildResolvedConfig(
      MachineConfigSchema.parse({}),
      ProjectConfigSchema.parse({})
    );
    world.generatedContent = staticcheckGenerator.generate(config);

    // Also execute the module to write the file
    const ctx = makeInitCtx(world.fm, [makeLanguagePlugin("go")]);
    await staticcheckConfigModule.execute(ctx);
  }
);

When<StaticcheckWorld>(
  "staticcheck detection runs",
  async (world: StaticcheckWorld) => {
    const ctx = makeInitCtx(world.fm, [makeLanguagePlugin("typescript")]);
    world.detected = await staticcheckConfigModule.detect(ctx);
  }
);

Then<StaticcheckWorld>(
  "the staticcheck output should contain {string}",
  (world: StaticcheckWorld, text: unknown) => {
    expect(world.generatedContent).toContain(String(text));
  }
);

Then<StaticcheckWorld>(
  "staticcheck should not be applicable",
  (world: StaticcheckWorld) => {
    expect(world.detected).toBe(false);
  }
);
