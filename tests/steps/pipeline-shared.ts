import type { World } from "@questi0nm4rk/feats";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import type { ReadlineHandle } from "@/init/prompt";
import type { PipelineContext, PipelineResult } from "@/pipelines/types";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

export interface PipelineWorld extends World {
  ctx: PipelineContext;
  result?: PipelineResult;
  inlineResult?: PipelineResult;
}

function freshConfig() {
  return buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse({})
  );
}

/** Readline factory that throws if called — use in non-TTY test contexts. */
export function noopReadline(): ReadlineHandle {
  throw new Error("createReadline called in a non-TTY test context");
}

export function makeBaseCtx(overrides: Partial<PipelineContext> = {}): PipelineContext {
  const fm = new FakeFileManager();
  fm.seed("/project/pyproject.toml", "[tool.ruff]");

  return {
    projectDir: "/project",
    config: freshConfig(),
    fileManager: fm,
    commandRunner: new FakeCommandRunner(),
    console: new FakeConsole(),
    flags: {},
    isTTY: false,
    createReadline: noopReadline,
    ...overrides,
  };
}

export function checkExitCode(result: PipelineResult): number {
  if (result.status === "ok") return 0;
  return (result.issueCount ?? 0) > 0 ? 1 : 2;
}

export function installExitCode(result: PipelineResult): number {
  return result.status === "error" ? 2 : 0;
}

export function makeRuffIssues(count: number): string {
  return JSON.stringify(
    Array.from({ length: count }, (_, i) => ({
      code: "E501",
      filename: `/project/foo${i}.py`,
      location: { row: i + 1, column: 1 },
      message: "Line too long",
    }))
  );
}
