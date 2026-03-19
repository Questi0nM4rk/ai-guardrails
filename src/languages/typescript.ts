import type { DetectOptions, LanguagePlugin } from "@/languages/types";
import { biomeRunner } from "@/runners/biome";
import { tscRunner } from "@/runners/tsc";
import type { LinterRunner } from "@/runners/types";

export const typescriptPlugin: LanguagePlugin = {
  id: "typescript",
  name: "TypeScript/JS",

  async detect({
    projectDir,
    fileManager,
    ignorePaths,
  }: DetectOptions): Promise<boolean> {
    if (await fileManager.exists(`${projectDir}/package.json`)) return true;
    const [tsFiles, jsFiles] = await Promise.all([
      fileManager.glob("**/*.ts", projectDir, ignorePaths),
      fileManager.glob("**/*.js", projectDir, ignorePaths),
    ]);
    return tsFiles.length > 0 || jsFiles.length > 0;
  },

  runners(): LinterRunner[] {
    return [biomeRunner, tscRunner];
  },
};
