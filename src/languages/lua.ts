import type { DetectOptions, LanguagePlugin } from "@/languages/types";
import { seleneRunner } from "@/runners/selene";
import type { LinterRunner } from "@/runners/types";

export const luaPlugin: LanguagePlugin = {
  id: "lua",
  name: "Lua",

  async detect({
    projectDir,
    fileManager,
    ignorePaths,
  }: DetectOptions): Promise<boolean> {
    const luaFiles = await fileManager.glob("**/*.lua", projectDir, ignorePaths);
    return luaFiles.length > 0;
  },

  runners(): LinterRunner[] {
    return [seleneRunner];
  },
};
