import type { DetectOptions, LanguagePlugin } from "@/languages/types";
import type { LinterRunner } from "@/runners/types";

export const dotnetPlugin: LanguagePlugin = {
  id: "dotnet",
  name: ".NET",

  async detect({
    projectDir,
    fileManager,
    ignorePaths,
  }: DetectOptions): Promise<boolean> {
    const [csprojFiles, slnFiles] = await Promise.all([
      fileManager.glob("**/*.csproj", projectDir, ignorePaths),
      fileManager.glob("**/*.sln", projectDir, ignorePaths),
    ]);
    return csprojFiles.length > 0 || slnFiles.length > 0;
  },

  runners(): LinterRunner[] {
    // TODO: implement dotnet-build + dotnet-format runners per SPEC-008
    // Deferred past v1 MVP — requires MSBuild JSON log parsing.
    return [];
  },
};
