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
  /** Stable identifier: "ruff", "pyright", "shellcheck", etc. */
  readonly id: string;
  /** Human-readable name */
  readonly name: string;
  /** Config file this runner manages, relative to project root. null = no config. */
  readonly configFile: string | null;
  /** Check if the tool binary is reachable */
  isAvailable(commandRunner: CommandRunner): Promise<boolean>;
  /** Run the linter, return normalized issues */
  run(opts: RunOptions): Promise<LintIssue[]>;
  /** Generate config file content. null = runner has no managed config. */
  generateConfig(config: ResolvedConfig): string | null;
}
