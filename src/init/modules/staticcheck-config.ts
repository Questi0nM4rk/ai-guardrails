import { staticcheckGenerator } from "@/generators/staticcheck";
import { writeConfigFile } from "@/init/modules/file-conflict";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const staticcheckConfigModule: InitModule = {
  id: "staticcheck-config",
  name: "Staticcheck Config",
  description: "Generate staticcheck.conf for Go static analysis",
  category: "language-config",
  defaultEnabled: true,
  disableFlag: "--no-staticcheck",
  dependsOn: ["config-tuning"],

  async detect(ctx: InitContext): Promise<boolean> {
    return ctx.languages.some((l) => l.id === "go");
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const content = staticcheckGenerator.generate(ctx.config);
    const force = ctx.flags.force === true;

    const result = await writeConfigFile(
      ctx.projectDir,
      staticcheckGenerator.configFile,
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
      message: `${staticcheckGenerator.configFile} written`,
      filesCreated: [staticcheckGenerator.configFile],
    };
  },
};
