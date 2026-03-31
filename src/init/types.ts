import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import type { ReadlineHandle } from "@/init/prompt";
import type { LanguagePlugin } from "@/languages/types";
import type { GitHubRepoInfo } from "@/utils/github-repo";

export type InitCategory =
  | "profile"
  | "language-config"
  | "universal-config"
  | "hooks"
  | "agent"
  | "ci"
  | "github"
  | "editor"
  | "tools"
  | "baseline";

export interface InitModuleResult {
  status: "ok" | "skipped" | "error";
  message: string;
  filesCreated?: readonly string[];
  filesModified?: readonly string[];
}

export interface InitContext {
  projectDir: string;
  fileManager: FileManager;
  commandRunner: CommandRunner;
  console: Console;
  config: ResolvedConfig;
  languages: LanguagePlugin[];
  selections: Map<string, boolean>;
  isTTY: boolean;
  createReadline: () => ReadlineHandle;
  flags: Record<string, unknown>;
  /** GitHub repo info, populated before module execution. Absent if not github.com. */
  github?: GitHubRepoInfo;
}

export interface InitModule {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly category: InitCategory;
  readonly defaultEnabled: boolean;
  readonly disableFlag?: string;
  readonly dependsOn?: readonly string[];
  detect(ctx: InitContext): Promise<boolean>;
  execute(ctx: InitContext): Promise<InitModuleResult>;
}
