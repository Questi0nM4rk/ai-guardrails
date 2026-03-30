import { describe, expect, test } from "bun:test";
import type { Interface as ReadlineInterface } from "node:readline";
import { stringify as stringifyToml } from "smol-toml";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { versionPinModule } from "@/init/modules/version-pin";
import type { InitContext } from "@/init/types";
import { PROJECT_CONFIG_PATH } from "@/models/paths";
import { getVersion } from "@/utils/version";
import { FakeCommandRunner } from "../../fakes/fake-command-runner";
import { FakeConsole } from "../../fakes/fake-console";
import { FakeFileManager } from "../../fakes/fake-file-manager";

const INSTALLED_VERSION = getVersion();

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

const CONFIG_PATH = `/project/${PROJECT_CONFIG_PATH}`;

describe("versionPinModule — basic properties", () => {
  test("detect always returns true", async () => {
    const ctx = makeCtx();
    expect(await versionPinModule.detect(ctx)).toBe(true);
  });
});

describe("versionPinModule — writes min_version when no existing pin", () => {
  test("creates config entry with installed version", async () => {
    const fm = new FakeFileManager();
    // Seed existing config (profile set by profile-selection module)
    fm.seed(CONFIG_PATH, stringifyToml({ profile: "standard" }));
    const ctx = makeCtx({ fileManager: fm });

    const result = await versionPinModule.execute(ctx);

    expect(result.status).toBe("ok");
    expect(result.message).toContain(INSTALLED_VERSION);

    const written = fm.written.find(([p]) => p === CONFIG_PATH);
    expect(written).toBeDefined();
    const content = written?.[1] ?? "";
    expect(content).toContain(`min_version = "${INSTALLED_VERSION}"`);
  });

  test("works when config file does not exist yet", async () => {
    const fm = new FakeFileManager();
    const ctx = makeCtx({ fileManager: fm });

    const result = await versionPinModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === CONFIG_PATH);
    expect(written).toBeDefined();
    const content = written?.[1] ?? "";
    expect(content).toContain(`min_version = "${INSTALLED_VERSION}"`);
  });
});

describe("versionPinModule — preserves higher existing pin", () => {
  test("preserves existing pin that is higher than installed version", async () => {
    const fm = new FakeFileManager();
    const higherPin = "99.0.0";
    fm.seed(
      CONFIG_PATH,
      stringifyToml({ profile: "standard", min_version: higherPin })
    );
    const cons = new FakeConsole();
    const ctx = makeCtx({ fileManager: fm, console: cons });

    const result = await versionPinModule.execute(ctx);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("preserved");
    // Should NOT have written a new lower version
    const writeWithLower = fm.written.find(([p, content]) => {
      if (p !== CONFIG_PATH) return false;
      return content.includes(`min_version = "${INSTALLED_VERSION}"`);
    });
    expect(writeWithLower).toBeUndefined();
    // Should warn
    expect(cons.warnings.some((w) => w.includes(higherPin))).toBe(true);
  });

  test("updates pin when existing pin is lower than installed version", async () => {
    const fm = new FakeFileManager();
    const lowerPin = "0.0.1";
    fm.seed(CONFIG_PATH, stringifyToml({ profile: "standard", min_version: lowerPin }));
    const ctx = makeCtx({ fileManager: fm });

    const result = await versionPinModule.execute(ctx);

    expect(result.status).toBe("ok");
    expect(result.message).toContain(INSTALLED_VERSION);
    const written = fm.written.find(([p]) => p === CONFIG_PATH);
    expect(written).toBeDefined();
    const content = written?.[1] ?? "";
    expect(content).toContain(`min_version = "${INSTALLED_VERSION}"`);
  });
});

describe("versionPinModule — --min-version flag override", () => {
  test("writes flag version instead of installed version", async () => {
    const fm = new FakeFileManager();
    fm.seed(CONFIG_PATH, stringifyToml({ profile: "standard" }));
    const ctx = makeCtx({ fileManager: fm, flags: { minVersion: "5.0.0" } });

    const result = await versionPinModule.execute(ctx);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("5.0.0");
    const written = fm.written.find(([p]) => p === CONFIG_PATH);
    const content = written?.[1] ?? "";
    expect(content).toContain('min_version = "5.0.0"');
  });

  test("--min-version overrides even a higher existing pin", async () => {
    const fm = new FakeFileManager();
    fm.seed(CONFIG_PATH, stringifyToml({ profile: "standard", min_version: "99.0.0" }));
    const ctx = makeCtx({ fileManager: fm, flags: { minVersion: "1.0.0" } });

    const result = await versionPinModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === CONFIG_PATH);
    const content = written?.[1] ?? "";
    expect(content).toContain('min_version = "1.0.0"');
  });

  test("ignores invalid flag value and falls back to installed version", async () => {
    const fm = new FakeFileManager();
    fm.seed(CONFIG_PATH, stringifyToml({ profile: "standard" }));
    const ctx = makeCtx({ fileManager: fm, flags: { minVersion: "not-a-version" } });

    const result = await versionPinModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p === CONFIG_PATH);
    const content = written?.[1] ?? "";
    expect(content).toContain(`min_version = "${INSTALLED_VERSION}"`);
  });
});
