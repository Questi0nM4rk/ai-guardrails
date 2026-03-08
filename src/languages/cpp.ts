import { clangTidyRunner } from "@/runners/clang-tidy";
import type { LinterRunner } from "@/runners/types";
import type { DetectOptions, LanguagePlugin } from "@/languages/types";

export const cppPlugin: LanguagePlugin = {
  id: "cpp",
  name: "C/C++",

  async detect({ projectDir, fileManager }: DetectOptions): Promise<boolean> {
    if (await fileManager.exists(`${projectDir}/CMakeLists.txt`)) return true;
    const cppFiles = await fileManager.glob("**/*.cpp", projectDir);
    if (cppFiles.length > 0) return true;
    const cFiles = await fileManager.glob("**/*.c", projectDir);
    return cFiles.length > 0;
  },

  runners(): LinterRunner[] {
    return [clangTidyRunner];
  },
};
