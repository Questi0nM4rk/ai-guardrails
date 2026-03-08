import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";

export interface PipelineContext {
  projectDir: string;
  languages: readonly LanguagePlugin[];
  config: ResolvedConfig;
  fileManager: FileManager;
  commandRunner: CommandRunner;
  console: Console;
  flags: Record<string, unknown>;
}

export interface PipelineResult {
  status: "ok" | "error";
  message?: string;
  issueCount?: number;
}

export interface Pipeline {
  run(ctx: PipelineContext): Promise<PipelineResult>;
}
