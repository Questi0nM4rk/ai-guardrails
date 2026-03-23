import { claudeSettingsGenerator } from "@/generators/claude-settings";
import { writeConfigFile } from "@/init/modules/file-conflict";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

export const claudeSettingsModule: InitModule = {
  id: "claude-settings",
  name: "Claude Settings",
  description: "Generate .claude/settings.json with PreToolUse hooks",
  category: "hooks",
  defaultEnabled: true,
  disableFlag: "--no-agent-hooks",
  dependsOn: ["config-tuning"],

  async detect(_ctx: InitContext): Promise<boolean> {
    return true;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const content = claudeSettingsGenerator.generate(ctx.config);
    const force = ctx.flags.force === true;

    const result = await writeConfigFile(
      ctx.projectDir,
      claudeSettingsGenerator.configFile,
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
      message: `${claudeSettingsGenerator.configFile} written`,
      filesCreated: [claudeSettingsGenerator.configFile],
    };
  },
};
