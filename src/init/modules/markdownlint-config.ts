import { markdownlintGenerator } from "@/generators/markdownlint";
import { writeConfigFile } from "@/init/modules/file-conflict";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const markdownlintConfigModule: InitModule = {
  id: "markdownlint-config",
  name: "Markdownlint Config",
  description: "Generate .markdownlint.jsonc for Markdown linting",
  category: "universal-config",
  defaultEnabled: true,
  disableFlag: "--no-markdownlint",
  dependsOn: ["config-tuning"],

  async detect(_ctx: InitContext): Promise<boolean> {
    return true;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const content = markdownlintGenerator.generate(ctx.config);
    const force = ctx.flags.force === true;

    const result = await writeConfigFile(
      ctx.projectDir,
      markdownlintGenerator.configFile,
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
      message: `${markdownlintGenerator.configFile} written`,
      filesCreated: [markdownlintGenerator.configFile],
    };
  },
};
