import { describe, expect, test } from "bun:test";
import type { FileManager } from "@/infra/file-manager";
import { setupCiStep } from "@/steps/setup-ci";
import { FakeFileManager } from "../fakes/fake-file-manager";

/** A FileManager that delegates to FakeFileManager but throws on writeText */
function makeFailingFileManager(): FileManager {
  const inner = new FakeFileManager();
  return {
    readText: (p) => inner.readText(p),
    writeText: async () => {
      throw new Error("disk full");
    },
    appendText: (p, c) => inner.appendText(p, c),
    exists: (p) => inner.exists(p),
    mkdir: (p, o) => inner.mkdir(p, o),
    glob: (p, c, i) => inner.glob(p, c, i),
    isSymlink: (p) => inner.isSymlink(p),
  };
}

describe("setupCiStep", () => {
  test("writes workflow file to .github/workflows/ai-guardrails.yml", async () => {
    const fm = new FakeFileManager();
    const result = await setupCiStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(fm.written).toHaveLength(1);
    const [path] = fm.written[0] ?? ["", ""];
    expect(path).toBe("/project/.github/workflows/ai-guardrails.yml");
  });

  test("workflow contains bun install --frozen-lockfile step", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toContain("bun install --frozen-lockfile");
  });

  test("install step has hashFiles condition", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toContain("hashFiles('bun.lock', 'bun.lockb') != ''");
  });

  test("step ordering: checkout then setup-bun then install then check", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm);

    const [, content] = fm.written[0] ?? ["", ""];
    const checkoutIdx = content.indexOf("actions/checkout@v4");
    const setupBunIdx = content.indexOf("oven-sh/setup-bun@v2");
    const installIdx = content.indexOf("bun install --frozen-lockfile");
    const checkIdx = content.indexOf("bunx ai-guardrails check");

    expect(checkoutIdx).toBeGreaterThanOrEqual(0);
    expect(setupBunIdx).toBeGreaterThan(checkoutIdx);
    expect(installIdx).toBeGreaterThan(setupBunIdx);
    expect(checkIdx).toBeGreaterThan(installIdx);
  });

  test("returns error when fileManager throws", async () => {
    const fm = makeFailingFileManager();

    const result = await setupCiStep("/project", fm);

    expect(result.status).toBe("error");
    if (result.status === "error") {
      expect(result.message).toContain("disk full");
    }
  });
});
