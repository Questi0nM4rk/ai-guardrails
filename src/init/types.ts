import type { Interface as ReadlineInterface } from "node:readline";
import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";

export type InitCategory =
  | "profile"
  | "language-config"
  | "universal-config"
  | "hooks"
  | "agent"
  | "ci"
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
  createReadline: () => ReadlineInterface;
  flags: Record<string, unknown>;
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
