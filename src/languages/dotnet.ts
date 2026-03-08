import type { LinterRunner } from "@/runners/types";
import type { DetectOptions, LanguagePlugin } from "@/languages/types";

export const dotnetPlugin: LanguagePlugin = {
  id: "dotnet",
  name: ".NET",

  async detect({ projectDir, fileManager }: DetectOptions): Promise<boolean> {
    const csprojFiles = await fileManager.glob("**/*.csproj", projectDir);
    if (csprojFiles.length > 0) return true;
    const slnFiles = await fileManager.glob("**/*.sln", projectDir);
    return slnFiles.length > 0;
  },

  runners(): LinterRunner[] {
    // dotnet-build runner is a stub — no implementation yet
    return [];
  },
};
