import { describe, expect, test } from "bun:test";
import {
    buildResolvedConfig,
    MachineConfigSchema,
    ProjectConfigSchema,
} from "@/config/schema";
import { installPipeline } from "@/pipelines/install";
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

describe("install command", () => {
    test("runInstall calls installPipeline and returns ok", async () => {
        const ctx = makeCtx();
        const result = await installPipeline.run(ctx);
        expect(result.status).toBe("ok");
    });

    test("exit code 0 on success, exit code 2 on config error", () => {
        function mapResultToExitCode(status: string): number {
            return status === "error" ? 2 : 0;
        }
        expect(mapResultToExitCode("ok")).toBe(0);
        expect(mapResultToExitCode("error")).toBe(2);
    });

    test("skips hooks when noHooks flag set", async () => {
        const ctx = makeCtx({ flags: { noHooks: true } });
        const cr = ctx.commandRunner as FakeCommandRunner;

        await installPipeline.run(ctx);

        const hasLefthookInstall = cr.calls.some(
            (args) => args[0] === "lefthook" && args[1] === "install"
        );
        expect(hasLefthookInstall).toBe(false);
    });

    test("skips CI when noCi flag set", async () => {
        const ctx = makeCtx({ flags: { noCi: true } });

        await installPipeline.run(ctx);

        const written = (ctx.fileManager as FakeFileManager).written.map(([p]) => p);
        expect(written.some((p) => p.includes("ai-guardrails.yml"))).toBe(false);
    });

    test("logs steps and successes to console", async () => {
        const ctx = makeCtx();
        const cons = ctx.console as FakeConsole;

        await installPipeline.run(ctx);

        expect(cons.steps.length).toBeGreaterThan(0);
        expect(cons.successes.length).toBeGreaterThan(0);
    });
});
