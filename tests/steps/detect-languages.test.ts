import { describe, expect, test } from "bun:test";
import { detectLanguagesStep } from "@/steps/detect-languages";
import { FakeFileManager } from "../fakes/fake-file-manager";

describe("detectLanguagesStep", () => {
  test("returns ok with detected languages for a python project", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/pyproject.toml", "[tool.ruff]");

    const { result, languages } = await detectLanguagesStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(languages.map((l) => l.id)).toContain("python");
    expect(languages.map((l) => l.id)).toContain("universal");
  });

  test("always includes universal plugin", async () => {
    const fm = new FakeFileManager();
    // No project files seeded

    const { result, languages } = await detectLanguagesStep("/empty", fm);

    expect(result.status).toBe("ok");
    expect(languages.map((l) => l.id)).toContain("universal");
  });

  test("detects multiple languages", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/pyproject.toml", "[tool.ruff]");
    fm.seed("/project/Cargo.toml", "[package]");

    const { result, languages } = await detectLanguagesStep("/project", fm);

    expect(result.status).toBe("ok");
    const ids = languages.map((l) => l.id);
    expect(ids).toContain("python");
    expect(ids).toContain("rust");
  });

  test("returns ok message listing language names", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/package.json", "{}");

    const { result } = await detectLanguagesStep("/project", fm);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("Detected");
  });
});
