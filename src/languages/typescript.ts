import { biomeRunner } from "@/runners/biome";
import { tscRunner } from "@/runners/tsc";
import type { LinterRunner } from "@/runners/types";
import type { DetectOptions, LanguagePlugin } from "@/languages/types";

export const typescriptPlugin: LanguagePlugin = {
  id: "typescript",
  name: "TypeScript/JS",

  async detect({ projectDir, fileManager }: DetectOptions): Promise<boolean> {
    if (await fileManager.exists(`${projectDir}/package.json`)) return true;
    const tsFiles = await fileManager.glob("**/*.ts", projectDir);
    if (tsFiles.length > 0) return true;
    const jsFiles = await fileManager.glob("**/*.js", projectDir);
    return jsFiles.length > 0;
  },

  runners(): LinterRunner[] {
    return [biomeRunner, tscRunner];
  },
};
