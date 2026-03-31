import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { staticcheckConfigModule } from "@/init/modules/staticcheck-config";
import type { InitContext } from "@/init/types";
import type { LanguagePlugin } from "@/languages/types";
import { FakeCommandRunner } from "../../fakes/fake-command-runner";
import { FakeConsole } from "../../fakes/fake-console";
import { FakeFileManager } from "../../fakes/fake-file-manager";

const goPlugin = { id: "go" } as LanguagePlugin;
const tsPlugin = { id: "typescript" } as LanguagePlugin;

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

describe("staticcheckConfigModule", () => {
  test("detect returns true when Go is detected", async () => {
    const ctx = makeCtx({ languages: [goPlugin] });
    expect(await staticcheckConfigModule.detect(ctx)).toBe(true);
  });

  test("detect returns false when Go is not detected", async () => {
    const ctx = makeCtx({ languages: [tsPlugin] });
    expect(await staticcheckConfigModule.detect(ctx)).toBe(false);
  });

  test("detect returns false for empty languages", async () => {
    const ctx = makeCtx({ languages: [] });
    expect(await staticcheckConfigModule.detect(ctx)).toBe(false);
  });

  test("execute writes staticcheck.conf", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm, languages: [goPlugin] });

    const result = await staticcheckConfigModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p.endsWith("staticcheck.conf"));
    expect(written).toBeDefined();
    expect(written?.[1]).toContain("[checks]");
    expect(written?.[1]).toContain('enabled = ["all"]');
  });

  test("execute skips when file exists and force is false", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/staticcheck.conf", "existing content");
    const ctx = makeCtx({ fileManager: fm, languages: [goPlugin] });

    const result = await staticcheckConfigModule.execute(ctx);

    expect(result.status).toBe("skipped");
  });

  test("execute overwrites when force is true", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/staticcheck.conf", "existing content");
    const ctx = makeCtx({
      fileManager: fm,
      languages: [goPlugin],
      flags: { force: true },
    });

    const result = await staticcheckConfigModule.execute(ctx);

    expect(result.status).toBe("ok");
  });
});
