import { dirname, join } from "node:path";
import { parse as parseToml, stringify as stringifyToml } from "smol-toml";
import { PROFILES, type Profile } from "@/config/schema";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import { PROJECT_CONFIG_PATH } from "@/models/paths";
import { isPlainObject } from "@/utils/deep-merge";

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
    const force = ctx.flags.force === true;
    const upgrade = ctx.flags.upgrade === true;

    const exists = await ctx.fileManager.exists(dest);

    if (exists && !force && !upgrade) {
      return {
        status: "skipped",
        message: `${PROJECT_CONFIG_PATH} already exists — use --force to overwrite or --upgrade to update profile`,
      };
    }

    // Read existing config to preserve all keys; only update the profile field.
    let existing: Record<string, unknown> = {};
    if (exists) {
      try {
        const text = await ctx.fileManager.readText(dest);
        const parsed: unknown = parseToml(text);
        existing = isPlainObject(parsed) ? parsed : {};
      } catch {
        // Cannot read existing file — start fresh
      }
    }

    const configData: Record<string, unknown> = { ...existing, profile };
    const content = stringifyToml(configData);

    try {
      await ctx.fileManager.mkdir(dirname(dest), { parents: true });
      await ctx.fileManager.writeText(dest, content);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e);
      return { status: "error", message: `Failed to write config: ${message}` };
    }

    if (exists) {
      return {
        status: "ok",
        message: `Config written with profile=${profile}`,
        filesModified: [PROJECT_CONFIG_PATH],
      };
    }
    return {
      status: "ok",
      message: `Config written with profile=${profile}`,
      filesCreated: [PROJECT_CONFIG_PATH],
    };
  },
};
