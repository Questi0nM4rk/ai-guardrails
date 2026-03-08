import { describe, expect, test } from "bun:test";
import type { InstallHint } from "@/runners/types";
import type { PrereqReport } from "@/steps/check-prerequisites";
import { installPrerequisites } from "@/steps/install-prerequisites";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";

function makeReport(missing: Array<{ id: string; hint: InstallHint }>): PrereqReport {
    return {
        missing: missing.map(({ id, hint }) => ({ runnerId: id, hint })),
        available: [],
    };
}

describe("installPrerequisites (non-TTY)", () => {
    // All tests run in non-TTY (CI) context so the interactive branch is not exercised.

    test("returns ok immediately when no tools are missing", async () => {
        const cr = new FakeCommandRunner();
        const cons = new FakeConsole();
        const report: PrereqReport = { missing: [], available: ["ruff"] };

        const result = await installPrerequisites(cons, cr, report, "/project");

        expect(result.status).toBe("ok");
        expect(cr.calls).toHaveLength(0);
    });

    test("prints missing tools with install command on non-TTY", async () => {
        const cr = new FakeCommandRunner();
        const cons = new FakeConsole();
        const report = makeReport([
            {
                id: "shellcheck",
                hint: { description: "Shell linter", brew: "brew install shellcheck" },
            },
        ]);

        // Ensure non-TTY path is taken (process.stdin.isTTY is undefined in test env)
        const result = await installPrerequisites(cons, cr, report, "/project");

        expect(result.status).toBe("ok");
        // Should have warned about the missing tool and printed the hint
        const allWarnings = cons.warnings.join("\n");
        expect(allWarnings).toContain("shellcheck");
        expect(allWarnings).toContain("brew install shellcheck");
        // Should NOT have tried to run any install command
        expect(cr.calls).toHaveLength(0);
    });

    test("prints first available install command in preference order (npm > pip > brew)", async () => {
        const cr = new FakeCommandRunner();
        const cons = new FakeConsole();
        const report = makeReport([
            {
                id: "pyright",
                hint: {
                    description: "Python type checker",
                    npm: "npm install -D pyright",
                    pip: "pip install pyright",
                },
            },
        ]);

        await installPrerequisites(cons, cr, report, "/project");

        const allWarnings = cons.warnings.join("\n");
        expect(allWarnings).toContain("npm install -D pyright");
    });

    test("handles missing tool with no install command gracefully", async () => {
        const cr = new FakeCommandRunner();
        const cons = new FakeConsole();
        const report = makeReport([
            { id: "unknown-tool", hint: { description: "Some obscure tool" } },
        ]);

        const result = await installPrerequisites(cons, cr, report, "/project");

        expect(result.status).toBe("ok");
    });
});
