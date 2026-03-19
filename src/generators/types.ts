import type { ResolvedConfig } from "@/config/schema";

export interface ConfigGenerator {
  /** Stable identifier: "ruff", "biome", "editorconfig", etc. */
  readonly id: string;
  /** Filename to write, relative to project root */
  readonly configFile: string;
  /** If set, this generator only runs when at least one of these languages is detected */
  readonly languages?: readonly string[];
  /** Generate config file content from resolved config */
  generate(config: ResolvedConfig): string;
}
