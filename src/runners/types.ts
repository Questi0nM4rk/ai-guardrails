import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { FileManager } from "@/infra/file-manager";
import type { LintIssue } from "@/models/lint-issue";

export interface RunOptions {
  projectDir: string;
  config: ResolvedConfig;
  commandRunner: CommandRunner;
  fileManager: FileManager;
}

export interface LinterRunner {
  readonly id: string;
  readonly name: string;
  readonly configFile: string | null;
  isAvailable(commandRunner: CommandRunner): Promise<boolean>;
  run(opts: RunOptions): Promise<LintIssue[]>;
  generateConfig(config: ResolvedConfig): string | null;
}
