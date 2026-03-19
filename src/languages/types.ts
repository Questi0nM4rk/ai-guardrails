import type { FileManager } from "@/infra/file-manager";
import type { LinterRunner } from "@/runners/types";

export interface DetectOptions {
  projectDir: string;
  fileManager: FileManager;
  ignorePaths?: readonly string[];
}

export interface LanguagePlugin {
  /** Stable identifier: "python", "typescript", "rust", etc. */
  readonly id: string;
  /** Human-readable name */
  readonly name: string;
  /** Return true if this language is present in the project */
  detect(opts: DetectOptions): Promise<boolean>;
  /** Runners to use when this language is active */
  runners(): LinterRunner[];
}
