import { describe, expect, test } from "bun:test";
import { ALL_PLUGINS, detectLanguages } from "@/languages/registry";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";

describe("ALL_PLUGINS", () => {
    test("contains 9 plugins", () => {
        expect(ALL_PLUGINS).toHaveLength(9);
    });

    test("universal plugin is last", () => {
        const last = ALL_PLUGINS[ALL_PLUGINS.length - 1];
        expect(last).toBeDefined();
        if (!last) return;
        expect(last.id).toBe("universal");
    });

    test("all plugin ids are unique", () => {
        const ids = ALL_PLUGINS.map((p) => p.id);
        const unique = new Set(ids);
        expect(unique.size).toBe(ids.length);
    });
});

describe("detectLanguages", () => {
    test("always includes universal plugin", async () => {
        const fm = new FakeFileManager();
        const active = await detectLanguages(PROJECT_DIR, fm);
        const ids = active.map((p) => p.id);
        expect(ids).toContain("universal");
    });

    test("detects python from pyproject.toml", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/pyproject.toml`, "[tool.ruff]");
        const active = await detectLanguages(PROJECT_DIR, fm);
        expect(active.map((p) => p.id)).toContain("python");
    });

    test("detects python from .py files", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/src/main.py`, "print('hello')");
        const active = await detectLanguages(PROJECT_DIR, fm);
        expect(active.map((p) => p.id)).toContain("python");
    });

    test("detects typescript from package.json", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/package.json`, '{"name":"foo"}');
        const active = await detectLanguages(PROJECT_DIR, fm);
        expect(active.map((p) => p.id)).toContain("typescript");
    });

    test("detects rust from Cargo.toml", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/Cargo.toml`, '[package]\nname = "foo"');
        const active = await detectLanguages(PROJECT_DIR, fm);
        expect(active.map((p) => p.id)).toContain("rust");
    });

    test("detects go from go.mod", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/go.mod`, "module example.com/foo");
        const active = await detectLanguages(PROJECT_DIR, fm);
        expect(active.map((p) => p.id)).toContain("go");
    });

    test("detects shell from .sh files", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/scripts/build.sh`, "#!/bin/bash");
        const active = await detectLanguages(PROJECT_DIR, fm);
        expect(active.map((p) => p.id)).toContain("shell");
    });

    test("detects cpp from CMakeLists.txt", async () => {
        const fm = new FakeFileManager();
        fm.seed(
            `${PROJECT_DIR}/CMakeLists.txt`,
            "cmake_minimum_required(VERSION 3.20)"
        );
        const active = await detectLanguages(PROJECT_DIR, fm);
        expect(active.map((p) => p.id)).toContain("cpp");
    });

    test("detects dotnet from .csproj", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/MyApp.csproj`, "<Project />");
        const active = await detectLanguages(PROJECT_DIR, fm);
        expect(active.map((p) => p.id)).toContain("dotnet");
    });

    test("detects lua from .lua files", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/src/main.lua`, "print('hello')");
        const active = await detectLanguages(PROJECT_DIR, fm);
        expect(active.map((p) => p.id)).toContain("lua");
    });

    test("returns only universal for empty project", async () => {
        const fm = new FakeFileManager();
        const active = await detectLanguages(PROJECT_DIR, fm);
        expect(active).toHaveLength(1);
        expect(active[0]?.id).toBe("universal");
    });

    test("returns plugins in priority order", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/pyproject.toml`, "");
        fm.seed(`${PROJECT_DIR}/Cargo.toml`, "");
        const active = await detectLanguages(PROJECT_DIR, fm);
        const ids = active.map((p) => p.id);
        const pythonIdx = ids.indexOf("python");
        const rustIdx = ids.indexOf("rust");
        expect(pythonIdx).toBeLessThan(rustIdx);
    });
});
