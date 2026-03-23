import { ruffGenerator } from "@/generators/ruff";
import { writeConfigFile } from "@/init/modules/file-conflict";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const ruffConfigModule: InitModule = {
  id: "ruff-config",
  name: "Ruff Config",
  description: "Generate ruff.toml for Python linting",
  category: "language-config",
  defaultEnabled: true,
  disableFlag: "--no-ruff",
  dependsOn: ["config-tuning"],

  async detect(ctx: InitContext): Promise<boolean> {
    return ctx.languages.some((l) => l.id === "python");
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const content = ruffGenerator.generate(ctx.config);
    const force = ctx.flags.force === true;

    const result = await writeConfigFile(
      ctx.projectDir,
      ruffGenerator.configFile,
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
      message: `${ruffGenerator.configFile} written`,
      filesCreated: [ruffGenerator.configFile],
    };
  },
};
