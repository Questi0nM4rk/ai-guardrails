import type { DetectOptions, LanguagePlugin } from "@/languages/types";
import { clippyRunner } from "@/runners/clippy";
import type { LinterRunner } from "@/runners/types";

export const rustPlugin: LanguagePlugin = {
    id: "rust",
    name: "Rust",

    async detect({ projectDir, fileManager }: DetectOptions): Promise<boolean> {
        return fileManager.exists(`${projectDir}/Cargo.toml`);
    },

    runners(): LinterRunner[] {
        return [clippyRunner];
    },
};
