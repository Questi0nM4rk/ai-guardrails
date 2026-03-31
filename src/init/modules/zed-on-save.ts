import { homedir } from "node:os";
import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

type JsonObject = Record<string, unknown>;

function mergeWithoutOverwrite(base: JsonObject, additions: JsonObject): JsonObject {
  const result: JsonObject = { ...base };
  for (const [key, value] of Object.entries(additions)) {
    if (!(key in result)) {
      result[key] = value;
    }
  }
  return result;
}

async function readJsonObject(
  path: string,
  fileManager: InitContext["fileManager"]
): Promise<JsonObject> {
  const exists = await fileManager.exists(path);
  if (!exists) return {};
  const text = await fileManager.readText(path);
  try {
    const parsed: unknown = JSON.parse(text);
    if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as JsonObject;
    }
    return {};
  } catch {
    return {};
  }
}

export const zedOnSaveModule: InitModule = {
  id: "zed-on-save",
  name: "Zed On-Save Formatting",
  description: "Configure Zed to format on save via .zed/settings.json",
  category: "editor",
  defaultEnabled: true,
  disableFlag: "--no-zed",
  dependsOn: ["biome-config", "ruff-config"],

  async detect(ctx: InitContext): Promise<boolean> {
    const hasZedConfig = await ctx.fileManager.exists(
      join(homedir(), ".config", "zed")
    );
    if (hasZedConfig) return true;

    const result = await ctx.commandRunner.run(["zed", "--version"], {
      cwd: ctx.projectDir,
    });
    return result.exitCode === 0;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const hasTs = ctx.languages.some((l) => l.id === "typescript");
    const hasPython = ctx.languages.some((l) => l.id === "python");

    const zedDir = join(ctx.projectDir, ".zed");
    const settingsPath = join(zedDir, "settings.json");

    await ctx.fileManager.mkdir(zedDir, { parents: true });

    const languages: JsonObject = {};
    if (hasTs) {
      languages.TypeScript = {
        formatter: {
          external: {
            command: "biome",
            arguments: ["format", "--write", "--stdin-file-path", "{buffer_path}"],
          },
        },
      };
      languages.JavaScript = {
        formatter: {
          external: {
            command: "biome",
            arguments: ["format", "--write", "--stdin-file-path", "{buffer_path}"],
          },
        },
      };
    }

    if (hasPython) {
      languages.Python = {
        formatter: {
          external: {
            command: "ruff",
            arguments: ["format", "-"],
          },
        },
      };
    }

    const additions: JsonObject = {
      format_on_save: "on",
      formatter: "language_server",
      languages,
    };

    const existing = await readJsonObject(settingsPath, ctx.fileManager);
    const merged = mergeWithoutOverwrite(existing, additions);
    await ctx.fileManager.writeText(settingsPath, JSON.stringify(merged, null, 2));

    return {
      status: "ok",
      message: ".zed/settings.json written",
      filesCreated: [".zed/settings.json"],
    };
  },
};
