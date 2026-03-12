import type { DetectOptions, LanguagePlugin } from "@/languages/types";
import { pyrightRunner } from "@/runners/pyright";
import { ruffRunner } from "@/runners/ruff";
import type { LinterRunner } from "@/runners/types";

export const pythonPlugin: LanguagePlugin = {
  id: "python",
  name: "Python",

  async detect({ projectDir, fileManager }: DetectOptions): Promise<boolean> {
    if (await fileManager.exists(`${projectDir}/pyproject.toml`)) return true;
    const pyFiles = await fileManager.glob("**/*.py", projectDir);
    return pyFiles.length > 0;
  },

  runners(): LinterRunner[] {
    return [ruffRunner, pyrightRunner];
  },
};
