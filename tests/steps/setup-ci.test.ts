import { describe, expect, test } from "bun:test";
import type { FileManager } from "@/infra/file-manager";
import { setupCiStep } from "@/steps/setup-ci";
import { FakeFileManager } from "../fakes/fake-file-manager";

const TS_ONLY = new Set(["typescript"]);
const PY_ONLY = new Set(["python"]);
const BOTH = new Set(["typescript", "python"]);
const NONE = new Set<string>();

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
    delete: (p) => inner.delete(p),
  };
}

describe("setupCiStep", () => {
  test("writes workflow file to .github/workflows/ai-guardrails.yml", async () => {
    const fm = new FakeFileManager();
    const result = await setupCiStep("/project", fm, TS_ONLY);

    expect(result.status).toBe("ok");
    expect(fm.written).toHaveLength(1);
    const [path] = fm.written[0] ?? ["", ""];
    expect(path).toBe("/project/.github/workflows/ai-guardrails.yml");
  });

  test("typescript project emits biome + tsc steps", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm, TS_ONLY);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toContain("bunx biome check .");
    expect(content).toContain("bunx tsc --noEmit");
    expect(content).toContain("oven-sh/setup-bun@v2");
    expect(content).toContain("bun install --frozen-lockfile");
    expect(content).toContain("hashFiles('bun.lock', 'bun.lockb') != ''");
  });

  test("typescript project does not emit python steps", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm, TS_ONLY);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).not.toContain("ruff check");
    expect(content).not.toContain("pyright");
    expect(content).not.toContain("setup-python");
    expect(content).not.toContain("pip install");
  });

  test("python project emits ruff + pyright steps", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm, PY_ONLY);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toContain("ruff check .");
    expect(content).toContain("pyright");
    expect(content).toContain("actions/setup-python@v5");
    expect(content).toContain('python-version: "3.12"');
    expect(content).toContain("pip install ruff pyright codespell");
  });

  test("python project does not emit typescript steps", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm, PY_ONLY);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).not.toContain("biome check");
    expect(content).not.toContain("tsc --noEmit");
    expect(content).not.toContain("setup-bun");
    expect(content).not.toContain("bun install");
  });

  test("multi-language project emits all steps", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm, BOTH);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toContain("bunx biome check .");
    expect(content).toContain("bunx tsc --noEmit");
    expect(content).toContain("ruff check .");
    expect(content).toContain("pyright");
    expect(content).toContain("oven-sh/setup-bun@v2");
    expect(content).toContain("actions/setup-python@v5");
    expect(content).toContain("pip install ruff pyright codespell");
    expect(content).toContain("bun install --frozen-lockfile");
  });

  test("empty language set emits only universal checks", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm, NONE);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toContain("codespell");
    expect(content).toContain("markdownlint-cli2");
    expect(content).toContain("gitleaks detect --no-banner");
    expect(content).not.toContain("biome");
    expect(content).not.toContain("tsc");
    expect(content).not.toContain("ruff");
    expect(content).not.toContain("pyright");
    expect(content).not.toContain("setup-bun");
    expect(content).not.toContain("setup-python");
  });

  test("universal checks always present regardless of language", async () => {
    for (const langs of [TS_ONLY, PY_ONLY, BOTH, NONE]) {
      const fm = new FakeFileManager();
      await setupCiStep("/project", fm, langs);

      const [, content] = fm.written[0] ?? ["", ""];
      expect(content).toContain('codespell --skip="*.lock,node_modules,dist" .');
      expect(content).toContain('bunx markdownlint-cli2 "**/*.md" "#node_modules"');
      expect(content).toContain("gitleaks detect --no-banner");
      expect(content).toContain("actions/checkout@v4");
    }
  });

  test("workflow does not reference ai-guardrails binary", async () => {
    for (const langs of [TS_ONLY, PY_ONLY, BOTH, NONE]) {
      const fm = new FakeFileManager();
      await setupCiStep("/project", fm, langs);

      const [, content] = fm.written[0] ?? ["", ""];
      expect(content).not.toContain("ai-guardrails");
      expect(content).not.toContain("install.sh");
    }
  });

  test("typescript workflow matches snapshot", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm, TS_ONLY);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toMatchSnapshot();
  });

  test("python workflow matches snapshot", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm, PY_ONLY);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toMatchSnapshot();
  });

  test("multi-language workflow matches snapshot", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm, BOTH);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toMatchSnapshot();
  });

  test("empty language workflow matches snapshot", async () => {
    const fm = new FakeFileManager();
    await setupCiStep("/project", fm, NONE);

    const [, content] = fm.written[0] ?? ["", ""];
    expect(content).toMatchSnapshot();
  });

  test("returns error when fileManager throws", async () => {
    const fm = makeFailingFileManager();

    const result = await setupCiStep("/project", fm, TS_ONLY);

    expect(result.status).toBe("error");
    if (result.status === "error") {
      expect(result.message).toContain("disk full");
    }
  });
});
