import { describe, expect, test } from "bun:test";
import { MANAGED_FILES, protectsFile } from "@/hooks/protect-configs";

describe("protectsFile", () => {
    // -----------------------------------------------------------------------
    // Each managed file should be blocked in write contexts
    // -----------------------------------------------------------------------
    for (const managed of MANAGED_FILES) {
        test(`blocks redirect write to ${managed}`, () => {
            expect(protectsFile(`echo "content" > ${managed}`)).not.toBeNull();
        });

        test(`blocks tee write to ${managed}`, () => {
            expect(protectsFile(`cat something | tee ${managed}`)).not.toBeNull();
        });

        test(`blocks sed -i on ${managed}`, () => {
            expect(protectsFile(`sed -i 's/foo/bar/' ${managed}`)).not.toBeNull();
        });
    }

    // -----------------------------------------------------------------------
    // Reading managed files should be allowed
    // -----------------------------------------------------------------------
    test("allows cat read of ruff.toml", () => {
        expect(protectsFile("cat ruff.toml")).toBeNull();
    });

    test("allows grep on biome.json", () => {
        expect(protectsFile("grep 'line' biome.json")).toBeNull();
    });

    test("allows reading AGENTS.md", () => {
        expect(protectsFile("cat AGENTS.md")).toBeNull();
    });

    // -----------------------------------------------------------------------
    // Unmanaged files should always be allowed
    // -----------------------------------------------------------------------
    test("allows writes to unmanaged files", () => {
        expect(protectsFile("echo hello > my-custom-config.yml")).toBeNull();
    });

    test("allows writes to src files", () => {
        expect(protectsFile("echo 'import x' > src/index.ts")).toBeNull();
    });

    // -----------------------------------------------------------------------
    // Return value
    // -----------------------------------------------------------------------
    test("returns reason string when blocked", () => {
        const reason = protectsFile("echo test > ruff.toml");
        expect(typeof reason).toBe("string");
        expect((reason ?? "").includes("ruff.toml")).toBe(true);
    });

    test("returns null when not blocked", () => {
        expect(protectsFile("echo hello")).toBeNull();
    });
});
