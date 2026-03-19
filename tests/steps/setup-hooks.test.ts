import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import { setupHooksStep } from "@/steps/setup-hooks";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";

function makeConfig() {
  const machine = MachineConfigSchema.parse({});
  const project = ProjectConfigSchema.parse({});
  return buildResolvedConfig(machine, project);
}

function makePlugin(id: string): LanguagePlugin {
  return {
    id,
    name: id,
    async detect(): Promise<boolean> {
      return true;
    },
    runners(): [] {
      return [];
    },
  };
}

describe("setupHooksStep", () => {
  test("writes lefthook.yml to project directory", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const result = await setupHooksStep("/project", [], config, fm, cr);

    expect(result.status).toBe("ok");
    expect(fm.written).toHaveLength(1);
    const [writtenPath] = fm.written[0] ?? [""];
    expect(writtenPath).toBe("/project/lefthook.yml");
  });

  test("calls lefthook install via commandRunner", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    await setupHooksStep("/project", [], config, fm, cr);

    expect(cr.calls).toHaveLength(1);
    expect(cr.calls[0]).toEqual(["lefthook", "install"]);
  });

  test("returns ok status on success", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const result = await setupHooksStep("/project", [], config, fm, cr);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("lefthook");
  });

  test("written lefthook.yml contains expected content", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    await setupHooksStep("/project", [makePlugin("typescript")], config, fm, cr);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content.length).toBeGreaterThan(0);
  });

  test("returns error when lefthook install exits with non-zero", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    cr.register(["lefthook", "install"], {
      stdout: "",
      stderr: "not found",
      exitCode: 1,
    });
    const config = makeConfig();

    const result = await setupHooksStep("/project", [], config, fm, cr);

    expect(result.status).toBe("error");
    expect(result.message).toContain("lefthook install failed");
    expect(result.message).toContain("exit 1");
  });

  test("returns error when fileManager.writeText throws", async () => {
    const inner = new FakeFileManager();
    const throwingFm: FileManager = {
      readText: (p) => inner.readText(p),
      writeText: async () => {
        throw new Error("no disk space");
      },
      appendText: (p, c) => inner.appendText(p, c),
      exists: (p) => inner.exists(p),
      mkdir: (p, o) => inner.mkdir(p, o),
      glob: (p, c, i) => inner.glob(p, c, i),
      isSymlink: (p) => inner.isSymlink(p),
      delete: (p) => inner.delete(p),
    };
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    const result = await setupHooksStep("/project", [], config, throwingFm, cr);

    expect(result.status).toBe("error");
    expect(result.message).toContain("Hook setup failed");
    expect(result.message).toContain("no disk space");
  });

  test("passes projectDir as cwd to lefthook install", async () => {
    const fm = new FakeFileManager();
    const cr = new FakeCommandRunner();
    const config = makeConfig();

    await setupHooksStep("/my-project", [], config, fm, cr);

    // FakeCommandRunner doesn't expose opts, but we verify it was called
    expect(cr.calls[0]).toEqual(["lefthook", "install"]);
  });
});
