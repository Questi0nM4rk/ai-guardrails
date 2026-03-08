import { describe, expect, test } from "bun:test";
import { isDangerous } from "@/hooks/dangerous-cmd";
import { DANGEROUS_DENY_GLOBS } from "@/hooks/dangerous-patterns";

describe("isDangerous", () => {
    // -----------------------------------------------------------------------
    // Blocked patterns
    // -----------------------------------------------------------------------
    test("blocks rm -rf /path", () => {
        expect(isDangerous("rm -rf /some/path")).not.toBeNull();
    });

    test("blocks rm -rf /", () => {
        expect(isDangerous("rm -rf /")).not.toBeNull();
    });

    test("blocks rm -rf trailing dir with slash", () => {
        expect(isDangerous("rm -rf /tmp/build/")).not.toBeNull();
    });

    test("blocks git push --force", () => {
        expect(isDangerous("git push origin main --force")).not.toBeNull();
    });

    test("blocks git push -f shorthand", () => {
        expect(isDangerous("git push -f origin main")).not.toBeNull();
    });

    test("blocks git reset --hard", () => {
        expect(isDangerous("git reset --hard HEAD~1")).not.toBeNull();
    });

    test("blocks git checkout --", () => {
        expect(isDangerous("git checkout -- .")).not.toBeNull();
    });

    test("blocks git clean -f", () => {
        expect(isDangerous("git clean -fd")).not.toBeNull();
    });

    test("blocks git clean -xf", () => {
        expect(isDangerous("git clean -xf")).not.toBeNull();
    });

    test("blocks git commit --no-verify", () => {
        expect(isDangerous('git commit -m "wip" --no-verify')).not.toBeNull();
    });

    // -----------------------------------------------------------------------
    // Safe commands that must NOT be blocked
    // -----------------------------------------------------------------------
    test("allows git push --force-with-lease", () => {
        expect(isDangerous("git push origin main --force-with-lease")).toBeNull();
    });

    test("allows regular rm command with file", () => {
        expect(isDangerous("rm foo.txt")).toBeNull();
    });

    test("allows git checkout branch name", () => {
        expect(isDangerous("git checkout main")).toBeNull();
    });

    test("allows git reset --soft", () => {
        expect(isDangerous("git reset --soft HEAD~1")).toBeNull();
    });

    test("allows normal git commit", () => {
        expect(isDangerous('git commit -m "fix: typo"')).toBeNull();
    });

    test("allows ls command", () => {
        expect(isDangerous("ls -la")).toBeNull();
    });

    test("allows ruff check", () => {
        expect(isDangerous("ruff check src/")).toBeNull();
    });

    test("allows rm -r without -f flag", () => {
        // rm -r without -f is not blocked
        expect(isDangerous("rm -r /tmp/somedir")).toBeNull();
    });

    test("returns reason string when blocked", () => {
        const reason = isDangerous("git reset --hard");
        expect(typeof reason).toBe("string");
        expect((reason ?? "").length).toBeGreaterThan(0);
    });
});

describe("DANGEROUS_DENY_GLOBS", () => {
    test("contains entry blocking bare --force", () => {
        expect(DANGEROUS_DENY_GLOBS).toContain("Bash(git push --force)");
    });

    test("contains entry blocking --force with branch arg", () => {
        expect(DANGEROUS_DENY_GLOBS).toContain("Bash(git push --force *)");
    });

    test("does not contain the old glob that matched --force-with-lease", () => {
        // The old "Bash(git push --force*)" glob (no space) matched --force-with-lease.
        // It must be replaced by the two precise entries above.
        expect(DANGEROUS_DENY_GLOBS).not.toContain("Bash(git push --force*)");
    });

    test("contains entry blocking -f shorthand with args", () => {
        expect(DANGEROUS_DENY_GLOBS).toContain("Bash(git push -f *)");
    });
});
