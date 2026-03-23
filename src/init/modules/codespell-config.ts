import { codespellGenerator } from "@/generators/codespell";
import { writeConfigFile } from "@/init/modules/file-conflict";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const codespellConfigModule: InitModule = {
  id: "codespell-config",
  name: "Codespell Config",
  description: "Generate .codespellrc for spell checking",
  category: "universal-config",
  defaultEnabled: true,
  disableFlag: "--no-codespell",
  dependsOn: ["config-tuning"],

  async detect(_ctx: InitContext): Promise<boolean> {
    return true;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const content = codespellGenerator.generate(ctx.config);
    const force = ctx.flags.force === true;

    const result = await writeConfigFile(
      ctx.projectDir,
      codespellGenerator.configFile,
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
      message: `${codespellGenerator.configFile} written`,
      filesCreated: [codespellGenerator.configFile],
    };
  },
};
