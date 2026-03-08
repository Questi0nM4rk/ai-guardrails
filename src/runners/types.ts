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

export interface InstallHint {
  /** Short description of the tool, e.g. "Python linter and formatter" */
  readonly description: string;
  /** npm install command, e.g. "npm install -D typescript" */
  readonly npm?: string;
  /** pip install command, e.g. "pip install ruff" */
  readonly pip?: string;
  /** Homebrew install command, e.g. "brew install shellcheck" */
  readonly brew?: string;
  /** apt install command, e.g. "sudo apt install shellcheck" */
  readonly apt?: string;
  /** cargo install command, e.g. "cargo install selene" */
  readonly cargo?: string;
  /** go install command */
  readonly go?: string;
  /** rustup component command, e.g. "rustup component add clippy" */
  readonly rustup?: string;
}

export interface LinterRunner {
  /** Stable identifier: "ruff", "pyright", "shellcheck", etc. */
  readonly id: string;
  /** Human-readable name */
  readonly name: string;
  /** Config file this runner manages, relative to project root. null = no config. */
  readonly configFile: string | null;
  /** Install instructions for this tool */
  readonly installHint: InstallHint;
  /** Check if the tool binary is reachable */
  isAvailable(commandRunner: CommandRunner): Promise<boolean>;
  /** Run the linter, return normalized issues */
  run(opts: RunOptions): Promise<LintIssue[]>;
  /** Generate config file content. null = runner has no managed config. */
  generateConfig(config: ResolvedConfig): string | null;
}
