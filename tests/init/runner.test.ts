import { describe, expect, test } from "bun:test";
import type { Interface as ReadlineInterface } from "node:readline";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { executeModules } from "@/init/runner";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

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
    createReadline: () =>
      ({
        question: (_q: string, cb: (a: string) => void) => cb(""),
        close: () => {},
      }) as unknown as ReadlineInterface,
    flags: {},
    ...overrides,
  };
}

function makeModule(
  id: string,
  opts?: {
    dependsOn?: readonly string[];
    executeResult?: InitModuleResult;
  }
): InitModule {
  const base: InitModule = {
    id,
    name: id,
    description: `${id} module`,
    category: "tools",
    defaultEnabled: true,
    detect: async () => true,
    execute: async () => opts?.executeResult ?? { status: "ok", message: `${id} done` },
  };
  if (opts?.dependsOn !== undefined) {
    return { ...base, dependsOn: opts.dependsOn };
  }
  return base;
}

describe("executeModules — selection filtering", () => {
  test("skips modules not in selections", async () => {
    const modules = [makeModule("a"), makeModule("b")];
    const selections = new Map([["a", true]]);
    const results = await executeModules(modules, makeCtx({ selections }));

    expect(results).toHaveLength(2);
    expect(results[0]?.status).toBe("ok");
    expect(results[1]?.status).toBe("skipped");
  });

  test("skips modules with selections.get(id) === false", async () => {
    const modules = [makeModule("a")];
    const selections = new Map([["a", false]]);
    const results = await executeModules(modules, makeCtx({ selections }));

    expect(results[0]?.status).toBe("skipped");
  });

  test("runs all modules when all selected", async () => {
    const modules = [makeModule("a"), makeModule("b")];
    const selections = new Map([
      ["a", true],
      ["b", true],
    ]);
    const results = await executeModules(modules, makeCtx({ selections }));

    expect(results.every((r) => r.status === "ok")).toBe(true);
  });
});

describe("executeModules — dependency ordering", () => {
  test("executes dependency before dependent", async () => {
    const order: string[] = [];
    const dep: InitModule = {
      ...makeModule("dep"),
      execute: async () => {
        order.push("dep");
        return { status: "ok", message: "dep done" };
      },
    };
    const main: InitModule = {
      ...makeModule("main"),
      dependsOn: ["dep"],
      execute: async () => {
        order.push("main");
        return { status: "ok", message: "main done" };
      },
    };
    // Provide modules in reverse order to confirm sort works
    const selections = new Map([
      ["dep", true],
      ["main", true],
    ]);
    await executeModules([main, dep], makeCtx({ selections }));

    expect(order).toEqual(["dep", "main"]);
  });

  test("handles a chain of three dependencies in order", async () => {
    const order: string[] = [];
    const track = (id: string): InitModule => ({
      ...makeModule(id),
      execute: async () => {
        order.push(id);
        return { status: "ok", message: `${id} done` };
      },
    });

    const a = track("a");
    const b: InitModule = { ...track("b"), dependsOn: ["a"] };
    const c: InitModule = { ...track("c"), dependsOn: ["b"] };

    const selections = new Map([
      ["a", true],
      ["b", true],
      ["c", true],
    ]);
    await executeModules([c, b, a], makeCtx({ selections }));

    expect(order).toEqual(["a", "b", "c"]);
  });
});

describe("executeModules — dependency failure propagation", () => {
  test("skips dependent when dependency errors", async () => {
    const dep = makeModule("dep", {
      executeResult: { status: "error", message: "dep failed" },
    });
    const dependent = makeModule("dependent", { dependsOn: ["dep"] });
    const selections = new Map([
      ["dep", true],
      ["dependent", true],
    ]);
    const results = await executeModules([dep, dependent], makeCtx({ selections }));

    expect(results[0]?.status).toBe("error");
    expect(results[1]?.status).toBe("skipped");
    expect(results[1]?.message).toMatch(/dep/);
  });

  test("skips dependent when dependency returns skipped", async () => {
    const dep = makeModule("dep", {
      executeResult: { status: "skipped", message: "already done" },
    });
    const dependent = makeModule("dependent", { dependsOn: ["dep"] });
    const selections = new Map([
      ["dep", true],
      ["dependent", true],
    ]);
    const results = await executeModules([dep, dependent], makeCtx({ selections }));

    expect(results[0]?.status).toBe("skipped");
    expect(results[1]?.status).toBe("skipped");
    expect(results[1]?.message).toMatch(/dep/);
  });

  test("does not skip dependent when dependency is not selected", async () => {
    // dep not in selections — dependent should still run (user opted out of dep)
    const dep = makeModule("dep");
    const dependent = makeModule("dependent", { dependsOn: ["dep"] });
    const selections = new Map([["dependent", true]]);
    const results = await executeModules([dep, dependent], makeCtx({ selections }));

    expect(results[0]?.status).toBe("skipped"); // dep not selected
    expect(results[1]?.status).toBe("ok"); // dependent still runs
  });

  test("runs dependent when all dependencies succeed", async () => {
    const dep = makeModule("dep", {
      executeResult: { status: "ok", message: "dep done" },
    });
    const dependent = makeModule("dependent", { dependsOn: ["dep"] });
    const selections = new Map([
      ["dep", true],
      ["dependent", true],
    ]);
    const results = await executeModules([dep, dependent], makeCtx({ selections }));

    expect(results[0]?.status).toBe("ok");
    expect(results[1]?.status).toBe("ok");
  });
});

describe("executeModules — circular dependency detection", () => {
  test("throws on direct cycle", async () => {
    const a: InitModule = { ...makeModule("a"), dependsOn: ["b"] };
    const b: InitModule = { ...makeModule("b"), dependsOn: ["a"] };
    const selections = new Map([
      ["a", true],
      ["b", true],
    ]);

    await expect(executeModules([a, b], makeCtx({ selections }))).rejects.toThrow(
      /[Cc]ircular/
    );
  });

  test("throws on indirect cycle a→b→c→a", async () => {
    const a: InitModule = { ...makeModule("a"), dependsOn: ["c"] };
    const b: InitModule = { ...makeModule("b"), dependsOn: ["a"] };
    const c: InitModule = { ...makeModule("c"), dependsOn: ["b"] };
    const selections = new Map([
      ["a", true],
      ["b", true],
      ["c", true],
    ]);

    await expect(executeModules([a, b, c], makeCtx({ selections }))).rejects.toThrow(
      /[Cc]ircular/
    );
  });
});

describe("executeModules — console output", () => {
  test("logs step and success for ok module", async () => {
    const cons = new FakeConsole();
    const modules = [makeModule("linter")];
    const selections = new Map([["linter", true]]);
    await executeModules(modules, makeCtx({ selections, console: cons }));

    expect(cons.steps.some((s) => s.includes("linter"))).toBe(true);
    expect(cons.successes.some((s) => s.includes("linter done"))).toBe(true);
  });

  test("logs error for error module", async () => {
    const cons = new FakeConsole();
    const errModule = makeModule("bad", {
      executeResult: { status: "error", message: "exploded" },
    });
    const selections = new Map([["bad", true]]);
    await executeModules([errModule], makeCtx({ selections, console: cons }));

    expect(cons.errors.some((s) => s.includes("exploded"))).toBe(true);
  });

  test("logs info for skipped module (from execute)", async () => {
    const cons = new FakeConsole();
    const skippedModule = makeModule("opt", {
      executeResult: { status: "skipped", message: "already configured" },
    });
    const selections = new Map([["opt", true]]);
    await executeModules([skippedModule], makeCtx({ selections, console: cons }));

    expect(cons.infos.some((s) => s.includes("already configured"))).toBe(true);
  });
});
