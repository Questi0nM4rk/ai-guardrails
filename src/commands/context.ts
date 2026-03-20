import { createInterface } from "node:readline";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { RealCommandRunner } from "@/infra/command-runner";
import { RealConsole } from "@/infra/console";
import { RealFileManager } from "@/infra/file-manager";
import type { PipelineContext } from "@/pipelines/types";

export function buildContext(
  projectDir: string,
  flags: Record<string, unknown> = {}
): PipelineContext {
  const machine = MachineConfigSchema.parse({});
  const project = ProjectConfigSchema.parse({});
  const config = buildResolvedConfig(machine, project);

  return {
    projectDir,
    config,
    fileManager: new RealFileManager(),
    commandRunner: new RealCommandRunner(),
    console: new RealConsole(),
    flags,
    isTTY: process.stdin.isTTY === true,
    createReadline: () =>
      createInterface({ input: process.stdin, output: process.stdout }),
  };
}
