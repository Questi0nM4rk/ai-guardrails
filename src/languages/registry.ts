import type { FileManager } from "@/infra/file-manager";
import { DEFAULT_IGNORE } from "@/languages/constants";
import { cppPlugin } from "@/languages/cpp";
import { dotnetPlugin } from "@/languages/dotnet";
import { goPlugin } from "@/languages/go";
import { luaPlugin } from "@/languages/lua";
import { pythonPlugin } from "@/languages/python";
import { rustPlugin } from "@/languages/rust";
import { shellPlugin } from "@/languages/shell";
import type { LanguagePlugin } from "@/languages/types";
import { typescriptPlugin } from "@/languages/typescript";
import { universalPlugin } from "@/languages/universal";

/** All built-in language plugins, in detection priority order. Universal is always last. */
export const ALL_PLUGINS: readonly LanguagePlugin[] = [
  pythonPlugin,
  typescriptPlugin,
  rustPlugin,
  goPlugin,
  shellPlugin,
  cppPlugin,
  dotnetPlugin,
  luaPlugin,
  universalPlugin,
];

/**
 * Detect which languages are present in the project.
 * Returns active plugins in priority order.
 * Universal plugin is always included.
 */
export async function detectLanguages(
  projectDir: string,
  fileManager: FileManager,
  ignorePaths?: readonly string[]
): Promise<LanguagePlugin[]> {
  const mergedIgnore: readonly string[] = [...DEFAULT_IGNORE, ...(ignorePaths ?? [])];
  const results = await Promise.all(
    ALL_PLUGINS.map(async (plugin) => ({
      plugin,
      active: await plugin.detect({
        projectDir,
        fileManager,
        ignorePaths: mergedIgnore,
      }),
    }))
  );
  return results.filter((r) => r.active).map((r) => r.plugin);
}
