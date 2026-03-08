import { describe, expect, test } from "bun:test";
import { FakeFileManager } from "../fakes/fake-file-manager";

describe("FakeFileManager", () => {
    test("readText throws for missing file", async () => {
        const fm = new FakeFileManager();
        expect(fm.readText("/missing.txt")).rejects.toThrow(
            "File not found: /missing.txt"
        );
    });

    test("readText returns seeded content", async () => {
        const fm = new FakeFileManager();
        fm.seed("/hello.txt", "hello world");
        const content = await fm.readText("/hello.txt");
        expect(content).toBe("hello world");
    });

    test("writeText stores content and tracks in written", async () => {
        const fm = new FakeFileManager();
        await fm.writeText("/out.txt", "content");
        const content = await fm.readText("/out.txt");
        expect(content).toBe("content");
        expect(fm.written).toHaveLength(1);
        expect(fm.written[0]).toEqual(["/out.txt", "content"]);
    });

    test("writeText overwrites existing content", async () => {
        const fm = new FakeFileManager();
        fm.seed("/file.txt", "old");
        await fm.writeText("/file.txt", "new");
        expect(await fm.readText("/file.txt")).toBe("new");
    });

    test("appendText appends to existing content", async () => {
        const fm = new FakeFileManager();
        fm.seed("/log.txt", "line1\n");
        await fm.appendText("/log.txt", "line2\n");
        expect(await fm.readText("/log.txt")).toBe("line1\nline2\n");
    });

    test("appendText creates file if not existing", async () => {
        const fm = new FakeFileManager();
        await fm.appendText("/new.txt", "content");
        expect(await fm.readText("/new.txt")).toBe("content");
    });

    test("exists returns true for seeded files", async () => {
        const fm = new FakeFileManager();
        fm.seed("/exists.txt", "");
        expect(await fm.exists("/exists.txt")).toBe(true);
    });

    test("exists returns false for missing files", async () => {
        const fm = new FakeFileManager();
        expect(await fm.exists("/missing.txt")).toBe(false);
    });

    test("exists returns true after writeText", async () => {
        const fm = new FakeFileManager();
        await fm.writeText("/created.txt", "content");
        expect(await fm.exists("/created.txt")).toBe(true);
    });

    test("glob matches files with pattern", async () => {
        const fm = new FakeFileManager();
        fm.seed("src/foo.ts", "");
        fm.seed("src/bar.ts", "");
        fm.seed("tests/baz.ts", "");
        const matches = await fm.glob("src/*.ts", "");
        expect(matches).toContain("src/foo.ts");
        expect(matches).toContain("src/bar.ts");
        expect(matches).not.toContain("tests/baz.ts");
    });

    test("glob with ** matches nested paths", async () => {
        const fm = new FakeFileManager();
        fm.seed("src/models/foo.ts", "");
        fm.seed("src/infra/bar.ts", "");
        fm.seed("README.md", "");
        const matches = await fm.glob("src/**/*.ts", "");
        expect(matches).toContain("src/models/foo.ts");
        expect(matches).toContain("src/infra/bar.ts");
        expect(matches).not.toContain("README.md");
    });

    test("isSymlink always returns false for fake", async () => {
        const fm = new FakeFileManager();
        expect(await fm.isSymlink("/any.txt")).toBe(false);
    });

    test("mkdir is a no-op", async () => {
        const fm = new FakeFileManager();
        await expect(fm.mkdir("/some/dir", { parents: true })).resolves.toBeUndefined();
    });
});
