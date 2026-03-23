import { editorconfigGenerator } from "@/generators/editorconfig";
import { writeConfigFile } from "@/init/modules/file-conflict";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const editorconfigModule: InitModule = {
  id: "editorconfig",
  name: "EditorConfig",
  description: "Generate .editorconfig for consistent editor settings",
  category: "universal-config",
  defaultEnabled: true,
  disableFlag: "--no-editorconfig",
  dependsOn: ["config-tuning"],

  async detect(_ctx: InitContext): Promise<boolean> {
    return true;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const content = editorconfigGenerator.generate(ctx.config);
    const force = ctx.flags.force === true;

    const result = await writeConfigFile(
      ctx.projectDir,
      editorconfigGenerator.configFile,
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
      message: `${editorconfigGenerator.configFile} written`,
      filesCreated: [editorconfigGenerator.configFile],
    };
  },
};
