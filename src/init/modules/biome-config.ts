import { biomeGenerator } from "@/generators/biome";
import { writeConfigFile } from "@/init/modules/file-conflict";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import { getBiomeVersion } from "@/runners/biome";
import { detectNoConsoleLevel } from "@/utils/detect-project-type";

async function readPackageJson(
  projectDir: string,
  fileManager: InitContext["fileManager"]
): Promise<unknown> {
  const pkgJsonPath = `${projectDir}/package.json`;
  const exists = await fileManager.exists(pkgJsonPath);
  if (!exists) return null;
  const text = await fileManager.readText(pkgJsonPath);
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export const biomeConfigModule: InitModule = {
  id: "biome-config",
  name: "Biome Config",
  description: "Generate biome.jsonc for TypeScript/JavaScript linting",
  category: "language-config",
  defaultEnabled: true,
  disableFlag: "--no-biome",
  dependsOn: ["config-tuning"],

  async detect(ctx: InitContext): Promise<boolean> {
    return ctx.languages.some((l) => l.id === "typescript");
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const [pkgJson, biomeVersion] = await Promise.all([
      readPackageJson(ctx.projectDir, ctx.fileManager),
      getBiomeVersion(ctx.commandRunner, ctx.projectDir),
    ]);

    const noConsoleLevel = detectNoConsoleLevel(pkgJson);

    const configWithMeta = {
      ...ctx.config,
      noConsoleLevel,
      values: {
        ...ctx.config.values,
        ...(biomeVersion !== undefined ? { biome_version: biomeVersion } : {}),
      },
    };

    const content = biomeGenerator.generate(configWithMeta);
    const force = ctx.flags.force === true;

    const result = await writeConfigFile(
      ctx.projectDir,
      biomeGenerator.configFile,
      content,
      force,
      ctx.fileManager
    );

    if (result.status === "skipped") {
      return { status: "skipped", message: result.reason };
    }
    if (result.status === "error") {
      return { status: "error", message: result.message };
    }

    return {
      status: "ok",
      message: `${biomeGenerator.configFile} written`,
      filesCreated: [biomeGenerator.configFile],
    };
  },
};
