import { golangciLintRunner } from "@/runners/golangci-lint";
import type { LinterRunner } from "@/runners/types";
import type { DetectOptions, LanguagePlugin } from "@/languages/types";

export const goPlugin: LanguagePlugin = {
  id: "go",
  name: "Go",

  async detect({ projectDir, fileManager }: DetectOptions): Promise<boolean> {
    return fileManager.exists(`${projectDir}/go.mod`);
  },

  runners(): LinterRunner[] {
    return [golangciLintRunner];
  },
};
