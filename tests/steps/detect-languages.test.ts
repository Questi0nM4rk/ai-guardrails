import { describe, expect, test } from "bun:test";
import type { FileManager } from "@/infra/file-manager";
import { detectLanguagesStep } from "@/steps/detect-languages";
import { FakeFileManager } from "../fakes/fake-file-manager";

describe("detectLanguagesStep", () => {
  test("returns detected languages with ok status", async () => {
    const fm = new FakeFileManager();
    // Seed a python file so the python plugin detects it
    fm.seed("/project/main.py", "print('hello')");

    const { result, languages } = await detectLanguagesStep("/project", fm);

    expect(result.status).toBe("ok");
    // universal plugin is always detected, plus any language-specific ones
    expect(languages.length).toBeGreaterThan(0);
  });

  test("returns ok status and includes universal plugin when no language files present", async () => {
    const fm = new FakeFileManager();
    // No files seeded → only universal plugin detected

    const { result, languages } = await detectLanguagesStep("/project", fm);

    expect(result.status).toBe("ok");
    // Universal is always last and always detected
    const ids = languages.map((p) => p.id);
    expect(ids).toContain("universal");
  });

  test("result message lists detected language names", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/main.py", "");

    const { result, languages } = await detectLanguagesStep("/project", fm);

    expect(result.status).toBe("ok");
    const names = languages.map((p) => p.name);
    for (const name of names) {
      expect(result.message).toContain(name);
    }
  });

  test("passes ignorePaths through to registry — ignored files not detected", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/src/main.py", "");

    // Without ignore, python IS detected (glob finds src/main.py)
    const { languages: withoutIgnore } = await detectLanguagesStep("/project", fm);
    const withoutIgnoreIds = withoutIgnore.map((p) => p.id);
    expect(withoutIgnoreIds).toContain("python");

    // With ignore covering the only python file, python is NOT detected
    const { result, languages: withIgnore } = await detectLanguagesStep(
      "/project",
      fm,
      ["src/**"]
    );

    expect(result.status).toBe("ok");
    const withIgnoreIds = withIgnore.map((p) => p.id);
    expect(withIgnoreIds).not.toContain("python");
  });

  test("returns error status on exception from fileManager", async () => {
    const innerFm = new FakeFileManager();
    // Make glob throw to trigger the catch path
    const throwingFm: FileManager = {
      readText: (p: string) => innerFm.readText(p),
      writeText: (p: string, c: string) => innerFm.writeText(p, c),
      appendText: (p: string, c: string) => innerFm.appendText(p, c),
      exists: (p: string) => innerFm.exists(p),
      mkdir: (p: string, o?: { parents?: boolean }) => innerFm.mkdir(p, o),
      glob: async (
        _p: string,
        _c: string,
        _i?: readonly string[]
      ): Promise<string[]> => {
        throw new Error("glob exploded");
      },
      isSymlink: (p: string) => innerFm.isSymlink(p),
      delete: (p: string) => innerFm.delete(p),
    };

    const { result, languages } = await detectLanguagesStep("/project", throwingFm);

    expect(result.status).toBe("error");
    expect(result.message).toContain("Language detection failed");
    expect(languages).toHaveLength(0);
  });
});

describe("detectLanguagesStep — direct plugin delegation", () => {
  test("returns ok with detected plugins and ok status", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/Cargo.toml", "[package]");

    const { result, languages } = await detectLanguagesStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(Array.isArray(languages)).toBe(true);
  });

  test("returns expected message format when universal is the only detected plugin", async () => {
    const fm = new FakeFileManager();
    // Only seed a non-language-specific file
    fm.seed("/project/README.md", "# Hello");

    const { result } = await detectLanguagesStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("Detected languages:");
  });
});
