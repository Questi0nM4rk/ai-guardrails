import type { FileManager } from "@/infra/file-manager";
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
  fileManager: FileManager
): Promise<LanguagePlugin[]> {
  const results = await Promise.all(
    ALL_PLUGINS.map(async (plugin) => ({
      plugin,
      active: await plugin.detect({ projectDir, fileManager }),
    }))
  );
  return results.filter((r) => r.active).map((r) => r.plugin);
}
