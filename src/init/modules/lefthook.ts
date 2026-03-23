import { generateLefthookConfig, lefthookGenerator } from "@/generators/lefthook";
import { writeConfigFile } from "@/init/modules/file-conflict";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const lefthookModule: InitModule = {
  id: "lefthook",
  name: "Lefthook",
  description: "Generate lefthook.yml and run lefthook install",
  category: "hooks",
  defaultEnabled: true,
  disableFlag: "--no-hooks",
  dependsOn: ["config-tuning"],

  async detect(_ctx: InitContext): Promise<boolean> {
    return true;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const content = generateLefthookConfig(ctx.config, ctx.languages);
    const force = ctx.flags.force === true;

    const writeResult = await writeConfigFile(
      ctx.projectDir,
      lefthookGenerator.configFile,
      content,
      force,
      ctx.fileManager
    );

    if (writeResult.status === "skipped") {
      return { status: "skipped", message: writeResult.reason };
    }
    if (writeResult.status === "error") {
      return { status: "error", message: writeResult.message };
    }

    try {
      const installResult = await ctx.commandRunner.run(["lefthook", "install"], {
        cwd: ctx.projectDir,
      });

      if (installResult.exitCode !== 0) {
        ctx.console.warning(
          `lefthook install failed (exit ${installResult.exitCode}) — install lefthook manually`
        );
      }
    } catch {
      ctx.console.warning(
        "lefthook not found — install it to activate pre-commit hooks"
      );
    }

    return {
      status: "ok",
      message: "lefthook.yml written and hooks installed",
      filesCreated: [lefthookGenerator.configFile],
    };
  },
};
