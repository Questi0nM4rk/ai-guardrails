import { seleneRunner } from "@/runners/selene";
import type { LinterRunner } from "@/runners/types";
import type { DetectOptions, LanguagePlugin } from "@/languages/types";

export const luaPlugin: LanguagePlugin = {
  id: "lua",
  name: "Lua",

  async detect({ projectDir, fileManager }: DetectOptions): Promise<boolean> {
    const luaFiles = await fileManager.glob("**/*.lua", projectDir);
    return luaFiles.length > 0;
  },

  runners(): LinterRunner[] {
    return [seleneRunner];
  },
};
