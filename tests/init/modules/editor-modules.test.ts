import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { helixOnSaveModule } from "@/init/modules/helix-on-save";
import { nvimOnSaveModule } from "@/init/modules/nvim-on-save";
import { vscodeOnSaveModule } from "@/init/modules/vscode-on-save";
import { zedOnSaveModule } from "@/init/modules/zed-on-save";
import type { InitContext } from "@/init/types";
import { isJsonObject } from "@/utils/json-merge";
import { FakeCommandRunner } from "../../fakes/fake-command-runner";
import { FakeConsole } from "../../fakes/fake-console";
import { FakeFileManager } from "../../fakes/fake-file-manager";
import { makePlugin } from "../../fakes/fake-language-plugin";

function makeCtx(overrides?: Partial<InitContext>): InitContext {
  const config = buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse({})
  );
  return {
    projectDir: "/project",
    fileManager: new FakeFileManager(),
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

// ---------------------------------------------------------------------------
// vscode-on-save
// ---------------------------------------------------------------------------

describe("vscode-on-save writes settings.json for typescript project", () => {
  test("creates settings.json with biome formatter entries", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    const result = await vscodeOnSaveModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === "/project/.vscode/settings.json");
    expect(written).toBeDefined();
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(parsed).toMatchObject({
      "editor.formatOnSave": true,
      "[typescript]": { "editor.defaultFormatter": "biomejs.biome" },
      "[javascript]": { "editor.defaultFormatter": "biomejs.biome" },
    });
  });

  test("does not include python sections for typescript-only project", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    await vscodeOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.vscode/settings.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(parsed["ruff.enable"]).toBeUndefined();
    expect(parsed["[python]"]).toBeUndefined();
  });
});

describe("vscode-on-save writes settings.json for python project", () => {
  test("creates settings.json with ruff formatter entries", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("python")] });

    const result = await vscodeOnSaveModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === "/project/.vscode/settings.json");
    expect(written).toBeDefined();
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(parsed).toMatchObject({
      "editor.formatOnSave": true,
      "ruff.enable": true,
      "ruff.fixAll": true,
      "ruff.organizeImports": true,
    });
  });

  test("does not include biome sections for python-only project", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("python")] });

    await vscodeOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.vscode/settings.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(parsed["[typescript]"]).toBeUndefined();
    expect(parsed["editor.codeActionsOnSave"]).toBeUndefined();
  });
});

describe("vscode-on-save merges without overwriting existing keys", () => {
  test("preserves user's existing formatter preference", async () => {
    const fm = new FakeFileManager();
    const existingSettings = JSON.stringify({
      "editor.formatOnSave": false,
      "[typescript]": { "editor.defaultFormatter": "esbenp.prettier-vscode" },
    });
    fm.seed("/project/.vscode/settings.json", existingSettings);
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    await vscodeOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.vscode/settings.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    // User's values are preserved
    expect(parsed["editor.formatOnSave"]).toBe(false);
    const tsSection = parsed["[typescript]"];
    expect(isJsonObject(tsSection)).toBe(true);
    if (!isJsonObject(tsSection)) return;
    expect(tsSection["editor.defaultFormatter"]).toBe("esbenp.prettier-vscode");
  });

  test("adds missing keys that are not already present", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.vscode/settings.json", JSON.stringify({ "editor.tabSize": 2 }));
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    await vscodeOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.vscode/settings.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(parsed["editor.tabSize"]).toBe(2);
    expect(parsed["editor.formatOnSave"]).toBe(true);
  });
});

describe("vscode-on-save writes extensions.json with detected language extensions", () => {
  test("includes biomejs.biome for typescript", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    await vscodeOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.vscode/extensions.json");
    expect(written).toBeDefined();
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(Array.isArray(parsed.recommendations)).toBe(true);
    expect(parsed.recommendations).toContain("biomejs.biome");
  });

  test("includes charliermarsh.ruff for python", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("python")] });

    await vscodeOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.vscode/extensions.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(parsed.recommendations).toContain("charliermarsh.ruff");
  });

  test("includes both extensions for typescript + python project", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({
      fileManager: fm,
      languages: [makePlugin("typescript"), makePlugin("python")],
    });

    await vscodeOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.vscode/extensions.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    const recs = Array.isArray(parsed.recommendations)
      ? parsed.recommendations.filter((r): r is string => typeof r === "string")
      : [];
    expect(recs).toContain("biomejs.biome");
    expect(recs).toContain("charliermarsh.ruff");
  });

  test("does not duplicate extensions when extensions.json already has them", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      "/project/.vscode/extensions.json",
      JSON.stringify({ recommendations: ["biomejs.biome"] })
    );
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    await vscodeOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.vscode/extensions.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    const recs = Array.isArray(parsed.recommendations)
      ? parsed.recommendations.filter((r): r is string => typeof r === "string")
      : [];
    const biomeCount = recs.filter((r) => r === "biomejs.biome").length;
    expect(biomeCount).toBe(1);
  });
});

describe("vscode-on-save skips when no supported languages", () => {
  test("returns skipped for empty languages array", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [] });

    const result = await vscodeOnSaveModule.execute(ctx);

    expect(result.status).toBe("skipped");
    // Must not write any files
    expect(fm.written.find(([p]) => p.includes(".vscode"))).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// helix-on-save
// ---------------------------------------------------------------------------

describe("helix-on-save writes languages.toml for typescript", () => {
  test("creates .helix/languages.toml with typescript sections", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    const result = await helixOnSaveModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === "/project/.helix/languages.toml");
    expect(written).toBeDefined();
    const content = written?.[1] ?? "";
    expect(content).toContain('name = "typescript"');
    expect(content).toContain('name = "javascript"');
    expect(content).toContain("biome");
    expect(content).not.toContain('name = "python"');
  });

  test("creates .helix/languages.toml with python section", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("python")] });

    const result = await helixOnSaveModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === "/project/.helix/languages.toml");
    expect(written).toBeDefined();
    const content = written?.[1] ?? "";
    expect(content).toContain('name = "python"');
    expect(content).toContain("ruff");
    expect(content).not.toContain('name = "typescript"');
  });

  test("includes both sections for typescript + python project", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({
      fileManager: fm,
      languages: [makePlugin("typescript"), makePlugin("python")],
    });

    await helixOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.helix/languages.toml");
    const content = written?.[1] ?? "";
    expect(content).toContain('name = "typescript"');
    expect(content).toContain('name = "python"');
  });
});

describe("helix-on-save skips when file exists", () => {
  test("returns skipped when .helix/languages.toml already exists", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.helix/languages.toml", "# existing config");
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    const result = await helixOnSaveModule.execute(ctx);

    expect(result.status).toBe("skipped");
    // Must not overwrite the existing file
    const written = fm.written.find(([p]) => p === "/project/.helix/languages.toml");
    expect(written).toBeUndefined();
  });
});

describe("helix-on-save skips when no supported languages", () => {
  test("returns skipped for empty languages array", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [] });

    const result = await helixOnSaveModule.execute(ctx);

    expect(result.status).toBe("skipped");
  });
});

// ---------------------------------------------------------------------------
// nvim-on-save
// ---------------------------------------------------------------------------

describe("nvim-on-save writes conform.lua", () => {
  test("creates .nvim/conform.lua for typescript project", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    const result = await nvimOnSaveModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === "/project/.nvim/conform.lua");
    expect(written).toBeDefined();
    const content = written?.[1] ?? "";
    expect(content).toContain("typescript");
    expect(content).toContain("biome");
    expect(content).toContain("format_on_save");
    expect(content).not.toContain("ruff_format");
  });

  test("creates .nvim/conform.lua for python project", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("python")] });

    const result = await nvimOnSaveModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === "/project/.nvim/conform.lua");
    const content = written?.[1] ?? "";
    expect(content).toContain("ruff_format");
    expect(content).not.toContain('"biome"');
  });

  test("creates .nvim/conform.lua for typescript + python project", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({
      fileManager: fm,
      languages: [makePlugin("typescript"), makePlugin("python")],
    });

    const result = await nvimOnSaveModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === "/project/.nvim/conform.lua");
    const content = written?.[1] ?? "";
    expect(content).toContain("typescript");
    expect(content).toContain("ruff_format");
  });

  test("prints conform.nvim install hint", async () => {
    const fm = new FakeFileManager();
    const cons = new FakeConsole();
    const ctx = makeCtx({
      fileManager: fm,
      console: cons,
      languages: [makePlugin("typescript")],
    });

    await nvimOnSaveModule.execute(ctx);

    expect(cons.infos.some((m) => m.includes("conform.nvim"))).toBe(true);
  });
});

describe("nvim-on-save skips when file exists", () => {
  test("returns skipped when .nvim/conform.lua already exists", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.nvim/conform.lua", "-- existing config");
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    const result = await nvimOnSaveModule.execute(ctx);

    expect(result.status).toBe("skipped");
    const written = fm.written.find(([p]) => p === "/project/.nvim/conform.lua");
    expect(written).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// zed-on-save
// ---------------------------------------------------------------------------

describe("zed-on-save writes settings.json", () => {
  test("creates .zed/settings.json for typescript project", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    const result = await zedOnSaveModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === "/project/.zed/settings.json");
    expect(written).toBeDefined();
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(parsed).toMatchObject({
      format_on_save: "on",
      formatter: "language_server",
    });
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(isJsonObject(parsed.languages)).toBe(true);
    if (!isJsonObject(parsed.languages)) return;
    expect(parsed.languages.TypeScript).toBeDefined();
    expect(parsed.languages.JavaScript).toBeDefined();
    expect(parsed.languages.Python).toBeUndefined();
  });

  test("creates .zed/settings.json for python project", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("python")] });

    const result = await zedOnSaveModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === "/project/.zed/settings.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(isJsonObject(parsed.languages)).toBe(true);
    if (!isJsonObject(parsed.languages)) return;
    expect(parsed.languages.Python).toBeDefined();
    expect(parsed.languages.TypeScript).toBeUndefined();
  });

  test("includes both language sections for typescript + python project", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({
      fileManager: fm,
      languages: [makePlugin("typescript"), makePlugin("python")],
    });

    await zedOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.zed/settings.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(isJsonObject(parsed.languages)).toBe(true);
    if (!isJsonObject(parsed.languages)) return;
    expect(parsed.languages.TypeScript).toBeDefined();
    expect(parsed.languages.Python).toBeDefined();
  });
});

describe("zed-on-save merges without overwriting", () => {
  test("preserves existing user keys", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      "/project/.zed/settings.json",
      JSON.stringify({ format_on_save: "off", tab_size: 4 })
    );
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    await zedOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.zed/settings.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    // User's value is preserved
    expect(parsed.format_on_save).toBe("off");
    // New key added
    expect(parsed.tab_size).toBe(4);
  });

  test("adds missing keys that are not already present", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.zed/settings.json", JSON.stringify({ tab_size: 2 }));
    const ctx = makeCtx({ fileManager: fm, languages: [makePlugin("typescript")] });

    await zedOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.zed/settings.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(parsed.tab_size).toBe(2);
    expect(parsed.format_on_save).toBe("on");
    expect(parsed.languages).toBeDefined();
  });

  test("2-level merge: preserves existing language key while adding absent languages", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      "/project/.zed/settings.json",
      JSON.stringify({
        languages: {
          TypeScript: { formatter: { external: { command: "prettier" } } },
        },
      })
    );
    const ctx = makeCtx({
      fileManager: fm,
      languages: [makePlugin("typescript"), makePlugin("python")],
    });

    await zedOnSaveModule.execute(ctx);

    const written = fm.written.find(([p]) => p === "/project/.zed/settings.json");
    const parsed: unknown = JSON.parse(written?.[1] ?? "{}");
    expect(isJsonObject(parsed)).toBe(true);
    if (!isJsonObject(parsed)) return;
    expect(isJsonObject(parsed.languages)).toBe(true);
    if (!isJsonObject(parsed.languages)) return;
    // User's existing TypeScript formatter config is preserved (not overwritten by biome)
    const ts = parsed.languages.TypeScript;
    expect(isJsonObject(ts)).toBe(true);
    if (!isJsonObject(ts)) return;
    const formatter = ts.formatter;
    expect(isJsonObject(formatter)).toBe(true);
    if (!isJsonObject(formatter)) return;
    const ext = formatter.external;
    expect(isJsonObject(ext)).toBe(true);
    if (!isJsonObject(ext)) return;
    expect(ext.command).toBe("prettier");
    // Python was added because it was absent in the existing languages object
    expect(parsed.languages.Python).toBeDefined();
    // JavaScript was added because it was also absent
    expect(parsed.languages.JavaScript).toBeDefined();
  });
});
