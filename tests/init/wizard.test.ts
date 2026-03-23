import { describe, expect, test } from "bun:test";
import type { Interface as ReadlineInterface } from "node:readline";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import type { ReadlineHandle } from "@/init/prompt";
import type { InitContext, InitModule } from "@/init/types";
import { runWizard } from "@/init/wizard";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

/**
 * Creates a readline factory that returns answers in sequence.
 * Each call to the factory returns a fresh readline using the next answer.
 */
function fakeReadline(answers: string[]): () => ReadlineInterface {
  let idx = 0;
  return () => {
    const handle: ReadlineHandle = {
      question(_prompt: string, cb: (answer: string) => void): void {
        cb(answers[idx++] ?? "");
      },
      close(): void {},
    };
    return handle as unknown as ReadlineInterface;
  };
}

function makeCtx(answers: string[], overrides?: Partial<InitContext>): InitContext {
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
    isTTY: true,
    createReadline: fakeReadline(answers),
    flags: {},
    ...overrides,
  };
}

function makeModule(
  id: string,
  category: InitModule["category"],
  opts?: {
    defaultEnabled?: boolean;
    detects?: boolean;
    disableFlag?: string;
  }
): InitModule {
  const base: InitModule = {
    id,
    name: id,
    description: `${id} description`,
    category,
    defaultEnabled: opts?.defaultEnabled ?? true,
    detect: async () => opts?.detects ?? true,
    execute: async () => ({ status: "ok", message: `${id} done` }),
  };
  if (opts?.disableFlag !== undefined) {
    return { ...base, disableFlag: opts.disableFlag };
  }
  return base;
}

describe("runWizard — applicable filtering", () => {
  test("returns empty map when no modules are applicable", async () => {
    const modules = [makeModule("a", "tools", { detects: false })];
    const ctx = makeCtx([]);
    const selections = await runWizard(ctx, modules);
    expect(selections.size).toBe(0);
  });

  test("does not prompt for non-applicable modules", async () => {
    const applicable = makeModule("applicable", "tools", { detects: true });
    const notApplicable = makeModule("not-applicable", "tools", { detects: false });
    // Only one answer needed — only one prompt should be shown
    const ctx = makeCtx(["y"]);
    const selections = await runWizard(ctx, [applicable, notApplicable]);

    expect(selections.has("applicable")).toBe(true);
    expect(selections.has("not-applicable")).toBe(false);
  });

  test("prompts for all applicable modules", async () => {
    const modules = [
      makeModule("a", "tools", { detects: true }),
      makeModule("b", "tools", { detects: true }),
      makeModule("c", "tools", { detects: false }),
    ];
    // Two prompts — answer "y" to both
    const ctx = makeCtx(["y", "y"]);
    const selections = await runWizard(ctx, modules);

    expect(selections.has("a")).toBe(true);
    expect(selections.has("b")).toBe(true);
    expect(selections.has("c")).toBe(false);
  });
});

describe("runWizard — user selection", () => {
  test("records true when user answers y", async () => {
    const modules = [makeModule("tool", "tools")];
    const ctx = makeCtx(["y"]);
    const selections = await runWizard(ctx, modules);
    expect(selections.get("tool")).toBe(true);
  });

  test("records false when user answers n", async () => {
    const modules = [makeModule("tool", "tools")];
    const ctx = makeCtx(["n"]);
    const selections = await runWizard(ctx, modules);
    expect(selections.get("tool")).toBe(false);
  });

  test("uses module defaultEnabled=true on empty input", async () => {
    const modules = [makeModule("tool", "tools", { defaultEnabled: true })];
    const ctx = makeCtx([""]);
    const selections = await runWizard(ctx, modules);
    expect(selections.get("tool")).toBe(true);
  });

  test("uses module defaultEnabled=false on empty input", async () => {
    const modules = [makeModule("tool", "tools", { defaultEnabled: false })];
    const ctx = makeCtx([""]);
    const selections = await runWizard(ctx, modules);
    expect(selections.get("tool")).toBe(false);
  });
});

describe("runWizard — category grouping", () => {
  test("prints category header for each non-empty category", async () => {
    const cons = new FakeConsole();
    const modules = [makeModule("hook-a", "hooks"), makeModule("ci-a", "ci")];
    const ctx = makeCtx(["y", "y"], { console: cons });
    await runWizard(ctx, modules);

    const headerMessages = cons.infos.filter((m) => m.includes("──"));
    expect(headerMessages.some((m) => m.includes("Hooks"))).toBe(true);
    expect(headerMessages.some((m) => m.includes("CI Pipeline"))).toBe(true);
  });

  test("does not print header for categories with no applicable modules", async () => {
    const cons = new FakeConsole();
    const modules = [makeModule("tool-a", "tools")];
    const ctx = makeCtx(["y"], { console: cons });
    await runWizard(ctx, modules);

    const headers = cons.infos.filter((m) => m.includes("──"));
    // Only tools header should appear
    expect(headers).toHaveLength(1);
    expect(headers[0]).toContain("Tool Installation");
  });

  test("processes categories in display order", async () => {
    const cons = new FakeConsole();
    // Provide modules in reverse display order
    const modules = [
      makeModule("baseline-a", "baseline"),
      makeModule("profile-a", "profile"),
    ];
    const ctx = makeCtx(["y", "y"], { console: cons });
    await runWizard(ctx, modules);

    const headerMessages = cons.infos.filter((m) => m.includes("──"));
    const profileIdx = headerMessages.findIndex((m) => m.includes("Profile"));
    const baselineIdx = headerMessages.findIndex((m) => m.includes("Baseline"));
    // profile should come before baseline in display order
    expect(profileIdx).toBeLessThan(baselineIdx);
  });
});

describe("runWizard — multiple modules per category", () => {
  test("prompts for each module in a category", async () => {
    const modules = [
      makeModule("editorconfig", "universal-config"),
      makeModule("markdownlint", "universal-config"),
      makeModule("codespell", "universal-config"),
    ];
    const ctx = makeCtx(["y", "n", "y"]);
    const selections = await runWizard(ctx, modules);

    expect(selections.get("editorconfig")).toBe(true);
    expect(selections.get("markdownlint")).toBe(false);
    expect(selections.get("codespell")).toBe(true);
  });
});
