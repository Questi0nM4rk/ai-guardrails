import { describe, expect, test } from "bun:test";
import type { FileManager } from "@/infra/file-manager";
import { loadConfigStep } from "@/steps/load-config";
import { FakeFileManager } from "../fakes/fake-file-manager";

describe("loadConfigStep", () => {
  test("returns default config with ok status when no config files exist", async () => {
    const fm = new FakeFileManager();
    // No files seeded — both machine and project configs are absent

    const { result, config } = await loadConfigStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(config).not.toBeNull();
    if (config === null) return;
    expect(config.profile).toBe("standard");
  });

  test("parses valid project config TOML", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.ai-guardrails/config.toml", `profile = "strict"\n`);

    const { result, config } = await loadConfigStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(config).not.toBeNull();
    if (config === null) return;
    expect(config.profile).toBe("strict");
  });

  test("result message includes profile name", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.ai-guardrails/config.toml", `profile = "minimal"\n`);

    const { result, config } = await loadConfigStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("profile=minimal");
    expect(config).not.toBeNull();
  });

  test("returns error and null config on malformed TOML", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.ai-guardrails/config.toml", `this is [ not valid toml !!!\n`);

    const { result, config } = await loadConfigStep("/project", fm);

    expect(result.status).toBe("error");
    expect(result.message).toContain("Config load failed");
    expect(config).toBeNull();
  });

  test("returns error on Zod validation failure for invalid profile value", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.ai-guardrails/config.toml", `profile = "ultra-strict"\n`);

    const { result, config } = await loadConfigStep("/project", fm);

    expect(result.status).toBe("error");
    expect(config).toBeNull();
  });
});

describe("loadConfigStep — FileManager error handling", () => {
  test("returns ok with defaults when all FileManager reads throw", async () => {
    const inner = new FakeFileManager();
    const throwingFm: FileManager = {
      readText: async () => {
        throw new Error("I/O error");
      },
      writeText: (p, c) => inner.writeText(p, c),
      appendText: (p, c) => inner.appendText(p, c),
      exists: (p) => inner.exists(p),
      mkdir: (p, o) => inner.mkdir(p, o),
      glob: (p, c, i) => inner.glob(p, c, i),
      isSymlink: (p) => inner.isSymlink(p),
      delete: (p) => inner.delete(p),
    };

    // readTomlSafe catches all errors and returns {} — config falls back to defaults
    const { result } = await loadConfigStep("/project", throwingFm);
    expect(result.status).toBe("ok");
  });
});
