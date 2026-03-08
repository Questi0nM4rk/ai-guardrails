import { shellcheckRunner } from "@/runners/shellcheck";
import { shfmtRunner } from "@/runners/shfmt";
import type { LinterRunner } from "@/runners/types";
import type { DetectOptions, LanguagePlugin } from "@/languages/types";

export const shellPlugin: LanguagePlugin = {
  id: "shell",
  name: "Shell",

  async detect({ projectDir, fileManager }: DetectOptions): Promise<boolean> {
    const shFiles = await fileManager.glob("**/*.sh", projectDir);
    if (shFiles.length > 0) return true;
    const bashFiles = await fileManager.glob("**/*.bash", projectDir);
    if (bashFiles.length > 0) return true;
    const zshFiles = await fileManager.glob("**/*.zsh", projectDir);
    return zshFiles.length > 0;
  },

  runners(): LinterRunner[] {
    return [shellcheckRunner, shfmtRunner];
  },
};
