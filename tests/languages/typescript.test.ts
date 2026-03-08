import { describe, expect, test } from "bun:test";
import { typescriptPlugin } from "@/languages/typescript";
import { biomeRunner } from "@/runners/biome";
import { tscRunner } from "@/runners/tsc";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";

describe("typescriptPlugin.detect", () => {
    test("returns true when package.json exists", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/package.json`, '{"name":"foo"}');
        const result = await typescriptPlugin.detect({
            projectDir: PROJECT_DIR,
            fileManager: fm,
        });
        expect(result).toBe(true);
    });

    test("returns true when .ts files exist", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/src/index.ts`, "export {}");
        const result = await typescriptPlugin.detect({
            projectDir: PROJECT_DIR,
            fileManager: fm,
        });
        expect(result).toBe(true);
    });

    test("returns true when .js files exist", async () => {
        const fm = new FakeFileManager();
        fm.seed(`${PROJECT_DIR}/index.js`, 'console.log("hi")');
        const result = await typescriptPlugin.detect({
            projectDir: PROJECT_DIR,
            fileManager: fm,
        });
        expect(result).toBe(true);
    });

    test("returns false for empty project", async () => {
        const fm = new FakeFileManager();
        const result = await typescriptPlugin.detect({
            projectDir: PROJECT_DIR,
            fileManager: fm,
        });
        expect(result).toBe(false);
    });
});

describe("typescriptPlugin.runners", () => {
    test("returns biome and tsc", () => {
        const runners = typescriptPlugin.runners();
        const ids = runners.map((r) => r.id);
        expect(ids).toContain(biomeRunner.id);
        expect(ids).toContain(tscRunner.id);
        expect(runners).toHaveLength(2);
    });
});

describe("typescriptPlugin metadata", () => {
    test("id is typescript", () => {
        expect(typescriptPlugin.id).toBe("typescript");
    });
});
