import { describe, expect, test } from "bun:test";
import { scanFile } from "@/hooks/suppress-comments";

describe("scanFile", () => {
    // -----------------------------------------------------------------------
    // Language detection via extension
    // -----------------------------------------------------------------------
    test("detects shellcheck disable in .sh files", () => {
        const findings = scanFile(
            "script.sh",
            "# shellcheck disable=SC2086\necho $var\n"
        );
        expect(findings).toHaveLength(1);
        expect(findings[0]?.line).toBe(1);
    });

    test("detects shellcheck disable in .bash files", () => {
        const findings = scanFile("script.bash", "# shellcheck disable=SC2034\nx=1\n");
        expect(findings).toHaveLength(1);
    });

    test("detects shellcheck disable in .zsh files", () => {
        const findings = scanFile("config.zsh", "# shellcheck disable=SC2148\nx=1\n");
        expect(findings).toHaveLength(1);
    });

    test("detects shellcheck disable in .ksh files", () => {
        // Fix 7: .ksh was missing from EXT_TO_LANG
        const findings = scanFile(
            "script.ksh",
            "# shellcheck disable=SC2086\necho $var\n"
        );
        expect(findings).toHaveLength(1);
        expect(findings[0]?.line).toBe(1);
    });

    test("returns no findings for .ksh file without suppressions", () => {
        const findings = scanFile("script.ksh", "echo hello\n");
        expect(findings).toHaveLength(0);
    });

    test("returns no findings for unknown extension", () => {
        const findings = scanFile("data.csv", "# noqa\n");
        expect(findings).toHaveLength(0);
    });

    // -----------------------------------------------------------------------
    // Allow-comment bypass
    // -----------------------------------------------------------------------
    test("skips lines containing ai-guardrails-allow", () => {
        const findings = scanFile(
            "script.sh",
            '# shellcheck disable=SC2086  # ai-guardrails-allow: shellcheck/SC2086 "intentional"\n'
        );
        expect(findings).toHaveLength(0);
    });

    // -----------------------------------------------------------------------
    // Python suppression patterns
    // -----------------------------------------------------------------------
    test("detects # noqa in .py files", () => {
        const findings = scanFile("module.py", "x = 1  # noqa\n");
        expect(findings).toHaveLength(1);
    });

    test("detects # type: ignore in .py files", () => {
        const findings = scanFile("module.py", "x: int = 'bad'  # type: ignore\n");
        expect(findings).toHaveLength(1);
    });
});
