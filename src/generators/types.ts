import type { ResolvedConfig } from "@/config/schema";

export interface ConfigGenerator {
  /** Stable identifier: "ruff", "biome", "editorconfig", etc. */
  readonly id: string;
  /** Filename to write, relative to project root */
  readonly configFile: string;
  /** Generate config file content from resolved config */
  generate(config: ResolvedConfig): string;
}
