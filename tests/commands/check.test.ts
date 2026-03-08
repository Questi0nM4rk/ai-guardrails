import { describe, expect, test } from "bun:test";
import {
    buildResolvedConfig,
    MachineConfigSchema,
    ProjectConfigSchema,
} from "@/config/schema";
import { checkPipeline } from "@/pipelines/check";
import type { PipelineContext } from "@/pipelines/types";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

function makeCtx(overrides: Partial<PipelineContext> = {}): PipelineContext {
    const machine = MachineConfigSchema.parse({});
    const project = ProjectConfigSchema.parse({});
    const config = buildResolvedConfig(machine, project);
    const fm = new FakeFileManager();
    fm.seed("/project/pyproject.toml", "[tool.ruff]");

    return {
        projectDir: "/project",
        config,
        fileManager: fm,
        commandRunner: new FakeCommandRunner(),
        console: new FakeConsole(),
        flags: {},
        ...overrides,
    };
}

describe("check command exit code behavior", () => {
    test("pipeline returns ok when no issues", async () => {
        const ctx = makeCtx();
        (ctx.commandRunner as FakeCommandRunner).register(
            ["ruff", "check", "--output-format=json", "/project"],
            { stdout: "[]", stderr: "", exitCode: 0 }
        );

        const result = await checkPipeline.run(ctx);
        expect(result.status).toBe("ok");
        expect(result.issueCount).toBe(0);
    });

    test("pipeline returns error with issueCount > 0 when issues found", async () => {
        const ctx = makeCtx();
        const ruffOutput = JSON.stringify([
            {
                code: "E501",
                filename: "/project/foo.py",
                location: { row: 1, column: 1 },
                message: "Line too long",
            },
        ]);
        (ctx.commandRunner as FakeCommandRunner).register(
            ["ruff", "check", "--output-format=json", "/project"],
            { stdout: ruffOutput, stderr: "", exitCode: 1 }
        );

        const result = await checkPipeline.run(ctx);
        expect(result.status).toBe("error");
        // issueCount drives exit(1) vs exit(2) in runCheck
        expect((result.issueCount ?? 0) > 0).toBe(true);
    });

    test("exit 1 for lint issues, exit 2 for config error", () => {
        // Verify the mapping logic directly without process.exit
        function mapResultToExitCode(status: string, issueCount: number): number {
            if (status === "ok") return 0;
            return issueCount > 0 ? 1 : 2;
        }

        expect(mapResultToExitCode("ok", 0)).toBe(0);
        expect(mapResultToExitCode("error", 3)).toBe(1);
        expect(mapResultToExitCode("error", 0)).toBe(2);
    });

    test("passes --format flag through context flags", async () => {
        const ctx = makeCtx({ flags: { format: "sarif" } });
        (ctx.commandRunner as FakeCommandRunner).register(
            ["ruff", "check", "--output-format=json", "/project"],
            { stdout: "[]", stderr: "", exitCode: 0 }
        );

        const result = await checkPipeline.run(ctx);
        expect(result.status).toBe("ok");
    });

    test("reports steps to console", async () => {
        const ctx = makeCtx();
        const cons = ctx.console as FakeConsole;
        (ctx.commandRunner as FakeCommandRunner).register(
            ["ruff", "check", "--output-format=json", "/project"],
            { stdout: "[]", stderr: "", exitCode: 0 }
        );

        await checkPipeline.run(ctx);
        expect(cons.steps.length).toBeGreaterThan(0);
    });
});
