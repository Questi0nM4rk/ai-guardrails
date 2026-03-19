import type { DetectOptions, LanguagePlugin } from "@/languages/types";
import { clangTidyRunner } from "@/runners/clang-tidy";
import type { LinterRunner } from "@/runners/types";

export const cppPlugin: LanguagePlugin = {
  id: "cpp",
  name: "C/C++",

  async detect({
    projectDir,
    fileManager,
    ignorePaths,
  }: DetectOptions): Promise<boolean> {
    if (await fileManager.exists(`${projectDir}/CMakeLists.txt`)) return true;
    const [cppFiles, cFiles] = await Promise.all([
      fileManager.glob("**/*.cpp", projectDir, ignorePaths),
      fileManager.glob("**/*.c", projectDir, ignorePaths),
    ]);
    return cppFiles.length > 0 || cFiles.length > 0;
  },

  runners(): LinterRunner[] {
    return [clangTidyRunner];
  },
};
