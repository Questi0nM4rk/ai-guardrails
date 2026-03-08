import { describe, expect, test } from "bun:test";
import { pythonPlugin } from "@/languages/python";
import { pyrightRunner } from "@/runners/pyright";
import { ruffRunner } from "@/runners/ruff";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";

describe("pythonPlugin.detect", () => {
  test("returns true when pyproject.toml exists", async () => {
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/pyproject.toml`, "[tool.ruff]");
    const result = await pythonPlugin.detect({ projectDir: PROJECT_DIR, fileManager: fm });
    expect(result).toBe(true);
  });

  test("returns true when .py files exist", async () => {
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/src/app.py`, "x = 1");
    const result = await pythonPlugin.detect({ projectDir: PROJECT_DIR, fileManager: fm });
    expect(result).toBe(true);
  });

  test("returns false for empty project", async () => {
    const fm = new FakeFileManager();
    const result = await pythonPlugin.detect({ projectDir: PROJECT_DIR, fileManager: fm });
    expect(result).toBe(false);
  });
});

describe("pythonPlugin.runners", () => {
  test("returns ruff and pyright", () => {
    const runners = pythonPlugin.runners();
    const ids = runners.map((r) => r.id);
    expect(ids).toContain(ruffRunner.id);
    expect(ids).toContain(pyrightRunner.id);
    expect(runners).toHaveLength(2);
  });
});

describe("pythonPlugin metadata", () => {
  test("id is python", () => {
    expect(pythonPlugin.id).toBe("python");
  });
});
