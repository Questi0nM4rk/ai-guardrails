import type { DetectOptions, LanguagePlugin } from "@/languages/types";
import { shellcheckRunner } from "@/runners/shellcheck";
import { shfmtRunner } from "@/runners/shfmt";
import type { LinterRunner } from "@/runners/types";

export const shellPlugin: LanguagePlugin = {
    id: "shell",
    name: "Shell",

    async detect({ projectDir, fileManager }: DetectOptions): Promise<boolean> {
        const [shFiles, bashFiles, zshFiles] = await Promise.all([
            fileManager.glob("**/*.sh", projectDir),
            fileManager.glob("**/*.bash", projectDir),
            fileManager.glob("**/*.zsh", projectDir),
        ]);
        return shFiles.length > 0 || bashFiles.length > 0 || zshFiles.length > 0;
    },

    runners(): LinterRunner[] {
        return [shellcheckRunner, shfmtRunner];
    },
};
