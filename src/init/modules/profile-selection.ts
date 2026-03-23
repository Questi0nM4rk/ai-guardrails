import { dirname, join } from "node:path";
import { stringify as stringifyToml } from "smol-toml";
import { PROFILES, type Profile } from "@/config/schema";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import { PROJECT_CONFIG_PATH } from "@/models/paths";

function isProfile(value: unknown): value is Profile {
  return typeof value === "string" && PROFILES.some((p) => p === value);
}

function resolveProfile(flags: Record<string, unknown>): Profile {
  const flagProfile = flags.profile;
  if (isProfile(flagProfile)) return flagProfile;
  return "standard";
}

export const profileSelectionModule: InitModule = {
  id: "profile-selection",
  name: "Profile Selection",
  description: "Write .ai-guardrails/config.toml with the selected profile",
  category: "profile",
  defaultEnabled: true,

  async detect(_ctx: InitContext): Promise<boolean> {
    return true;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const profile = resolveProfile(ctx.flags);
    const dest = join(ctx.projectDir, PROJECT_CONFIG_PATH);

    const configData: Record<string, unknown> = { profile };
    const content = stringifyToml(configData);

    await ctx.fileManager.mkdir(dirname(dest), { parents: true });
    await ctx.fileManager.writeText(dest, content);

    return {
      status: "ok",
      message: `Config written with profile=${profile}`,
      filesCreated: [PROJECT_CONFIG_PATH],
    };
  },
};
