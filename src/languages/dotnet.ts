import type { DetectOptions, LanguagePlugin } from "@/languages/types";
import type { LinterRunner } from "@/runners/types";

export const dotnetPlugin: LanguagePlugin = {
    id: "dotnet",
    name: ".NET",

    async detect({ projectDir, fileManager }: DetectOptions): Promise<boolean> {
        const [csprojFiles, slnFiles] = await Promise.all([
            fileManager.glob("**/*.csproj", projectDir),
            fileManager.glob("**/*.sln", projectDir),
        ]);
        return csprojFiles.length > 0 || slnFiles.length > 0;
    },

    runners(): LinterRunner[] {
        // dotnet-build runner is a stub — no implementation yet
        return [];
    },
};
