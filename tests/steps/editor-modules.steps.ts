import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { helixOnSaveModule } from "@/init/modules/helix-on-save";
import { nvimOnSaveModule } from "@/init/modules/nvim-on-save";
import { vscodeOnSaveModule } from "@/init/modules/vscode-on-save";
import { zedOnSaveModule } from "@/init/modules/zed-on-save";
import type { InitContext, InitModuleResult } from "@/init/types";
import { isJsonObject } from "@/utils/json-merge";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";
import { makePlugin } from "../fakes/fake-language-plugin";

interface EditorWorld extends World {
  ctx: InitContext;
  fm: FakeFileManager;
  result?: InitModuleResult;
}

function makeEditorCtx(
  fm: FakeFileManager,
  overrides?: Partial<Omit<InitContext, "fileManager">>
): InitContext {
  const config = buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse({})
  );
  return {
    projectDir: "/project",
    fileManager: fm,
    commandRunner: new FakeCommandRunner(),
    console: new FakeConsole(),
    config,
    languages: [],
    selections: new Map(),
    isTTY: false,
    createReadline: () => ({
      question: (_q: string, cb: (a: string) => void) => cb(""),
      close: () => {},
    }),
    flags: {},
    ...overrides,
  };
}

// ── Given steps ───────────────────────────────────────────────────────────────

Given<EditorWorld>(
  "a TypeScript project for vscode on-save testing",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.ctx = makeEditorCtx(world.fm, { languages: [makePlugin("typescript")] });
  }
);

Given<EditorWorld>(
  "a Python project for vscode on-save testing",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.ctx = makeEditorCtx(world.fm, { languages: [makePlugin("python")] });
  }
);

Given<EditorWorld>(
  "a TypeScript project with existing VS Code settings",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.fm.seed(
      "/project/.vscode/settings.json",
      JSON.stringify({ "editor.tabSize": 4, "my.custom.key": "preserved" })
    );
    world.ctx = makeEditorCtx(world.fm, {
      languages: [makePlugin("typescript")],
    });
  }
);

Given<EditorWorld>(
  "a project with no supported languages for vscode",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.ctx = makeEditorCtx(world.fm, { languages: [] });
  }
);

Given<EditorWorld>(
  "a TypeScript project for helix on-save testing",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.ctx = makeEditorCtx(world.fm, { languages: [makePlugin("typescript")] });
  }
);

Given<EditorWorld>(
  "a project with an existing helix languages config",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.fm.seed("/project/.helix/languages.toml", "# existing helix config");
    world.ctx = makeEditorCtx(world.fm, {
      languages: [makePlugin("typescript")],
    });
  }
);

Given<EditorWorld>(
  "a project with no supported languages for helix",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.ctx = makeEditorCtx(world.fm, { languages: [] });
  }
);

Given<EditorWorld>(
  "a TypeScript project for nvim on-save testing",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.ctx = makeEditorCtx(world.fm, { languages: [makePlugin("typescript")] });
  }
);

Given<EditorWorld>(
  "a project with an existing nvim conform config",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.fm.seed("/project/.nvim/conform.lua", "-- existing conform config");
    world.ctx = makeEditorCtx(world.fm, {
      languages: [makePlugin("typescript")],
    });
  }
);

Given<EditorWorld>(
  "a TypeScript project for zed on-save testing",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.ctx = makeEditorCtx(world.fm, { languages: [makePlugin("typescript")] });
  }
);

Given<EditorWorld>(
  "a TypeScript project with existing Zed settings",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.fm.seed(
      "/project/.zed/settings.json",
      JSON.stringify({ tab_size: 4, "my.custom.key": "preserved" })
    );
    world.ctx = makeEditorCtx(world.fm, {
      languages: [makePlugin("typescript")],
    });
  }
);

Given<EditorWorld>(
  "a project with no supported languages for zed",
  async (world: EditorWorld) => {
    world.fm = new FakeFileManager();
    world.ctx = makeEditorCtx(world.fm, { languages: [] });
  }
);

// ── When steps ────────────────────────────────────────────────────────────────

When<EditorWorld>("the vscode-on-save module executes", async (world: EditorWorld) => {
  world.result = await vscodeOnSaveModule.execute(world.ctx);
});

When<EditorWorld>("the helix-on-save module executes", async (world: EditorWorld) => {
  world.result = await helixOnSaveModule.execute(world.ctx);
});

When<EditorWorld>("the nvim-on-save module executes", async (world: EditorWorld) => {
  world.result = await nvimOnSaveModule.execute(world.ctx);
});

When<EditorWorld>("the zed-on-save module executes", async (world: EditorWorld) => {
  world.result = await zedOnSaveModule.execute(world.ctx);
});

// ── Then steps ────────────────────────────────────────────────────────────────

Then<EditorWorld>(
  "the editor module should write {string}",
  async (world: EditorWorld, relPath: unknown) => {
    const fullPath = `/project/${String(relPath)}`;
    const written = world.fm.written.map(([p]) => p);
    expect(written).toContain(fullPath);
  }
);

Then<EditorWorld>(
  "the settings should contain {string}",
  async (world: EditorWorld, token: unknown) => {
    const settingsEntry = world.fm.written.find(([p]) => p.endsWith("settings.json"));
    expect(settingsEntry).toBeDefined();
    expect(settingsEntry?.[1]).toContain(String(token));
  }
);

Then<EditorWorld>(
  "the config should contain {string}",
  async (world: EditorWorld, token: unknown) => {
    const entry = world.fm.written[0];
    expect(entry).toBeDefined();
    expect(entry?.[1]).toContain(String(token));
  }
);

Then<EditorWorld>(
  "existing settings keys should be preserved",
  async (world: EditorWorld) => {
    const written = world.fm.written.find(([p]) => p.endsWith("settings.json"));
    expect(written).toBeDefined();
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(parsed["my.custom.key"]).toBe("preserved");
  }
);

Then<EditorWorld>(
  "existing Zed settings keys should be preserved",
  async (world: EditorWorld) => {
    const written = world.fm.written.find(([p]) => p.endsWith(".zed/settings.json"));
    expect(written).toBeDefined();
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(parsed["my.custom.key"]).toBe("preserved");
  }
);

Then<EditorWorld>(
  "extensions should recommend {string}",
  async (world: EditorWorld, ext: unknown) => {
    const written = world.fm.written.find(([p]) => p.endsWith("extensions.json"));
    expect(written).toBeDefined();
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(Array.isArray(parsed.recommendations)).toBe(true);
    expect(parsed.recommendations).toContain(String(ext));
  }
);

Then<EditorWorld>(
  "the module should return status {string}",
  async (world: EditorWorld, status: unknown) => {
    if (world.result === undefined) throw new Error("module result not set");
    const s: string = world.result.status;
    expect(s).toBe(String(status));
  }
);
