import type { DetectOptions, LanguagePlugin } from "@/languages/types";
import { shellcheckRunner } from "@/runners/shellcheck";
import { shfmtRunner } from "@/runners/shfmt";
import type { LinterRunner } from "@/runners/types";

export const shellPlugin: LanguagePlugin = {
    id: "shell",
    name: "Shell",

    async detect({ projectDir, fileManager }: DetectOptions): Promise<boolean> {
        const files = await fileManager.glob("**/*.{sh,bash,zsh,ksh}", projectDir);
        return files.length > 0;
    },

    runners(): LinterRunner[] {
        return [shellcheckRunner, shfmtRunner];
    },
};
