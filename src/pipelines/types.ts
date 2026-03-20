import type { Interface as ReadlineInterface } from "node:readline";
import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";

export interface PipelineContext {
  projectDir: string;
  config: ResolvedConfig;
  fileManager: FileManager;
  commandRunner: CommandRunner;
  console: Console;
  flags: Record<string, unknown>;
  isTTY: boolean;
  createReadline: () => ReadlineInterface;
}

export interface PipelineResult {
  status: "ok" | "error";
  message?: string;
  issueCount?: number;
}

export interface Pipeline {
  run(ctx: PipelineContext): Promise<PipelineResult>;
}
