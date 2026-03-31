import { join } from "node:path";
import { parse as parseToml, stringify as stringifyToml } from "smol-toml";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import { PROJECT_CONFIG_PATH } from "@/models/paths";
import { isPlainObject } from "@/utils/deep-merge";
import { getVersion, semverLt } from "@/utils/version";

function resolveMinVersion(flags: Record<string, unknown>): string {
  const flagVersion = flags.minVersion;
  if (typeof flagVersion === "string" && /^\d+\.\d+\.\d+$/.test(flagVersion)) {
    return flagVersion;
  }
  return getVersion();
}

export const versionPinModule: InitModule = {
  id: "version-pin",
  name: "Version Pinning",
  description: "Pin minimum ai-guardrails version in config",
  category: "profile",
  defaultEnabled: true,
  dependsOn: ["profile-selection"],

  async detect(_ctx: InitContext): Promise<boolean> {
    return true;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const dest = join(ctx.projectDir, PROJECT_CONFIG_PATH);
    const desired = resolveMinVersion(ctx.flags);

    // Read existing config to check for existing pin and preserve all keys.
    let existing: Record<string, unknown> = {};
    try {
      const text = await ctx.fileManager.readText(dest);
      const parsed: unknown = parseToml(text);
      existing = isPlainObject(parsed) ? parsed : {};
    } catch {
      // File may not exist yet — will be created by profile-selection module
    }

    const existingPin =
      typeof existing.min_version === "string" ? existing.min_version : undefined;

    // Idempotency rule: never downgrade the pin unless --min-version was
    // explicitly provided.
    const hasExplicitFlag =
      typeof ctx.flags.minVersion === "string" &&
      /^\d+\.\d+\.\d+$/.test(ctx.flags.minVersion);

    if (
      !hasExplicitFlag &&
      existingPin !== undefined &&
      semverLt(desired, existingPin)
    ) {
      ctx.console.warning(
        `Version pin preserved: project requires >=${existingPin} but installed ${desired}.\n` +
          `Use --min-version to override.`
      );
      return {
        status: "ok",
        message: `Version pin preserved at ${existingPin} (installed ${desired} is older)`,
      };
    }

    const updated: Record<string, unknown> = { ...existing, min_version: desired };

    try {
      await ctx.fileManager.writeText(dest, stringifyToml(updated));
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e);
      return { status: "error", message: `Failed to write config: ${message}` };
    }

    return {
      status: "ok",
      message: `min_version pinned to ${desired}`,
      filesModified: [PROJECT_CONFIG_PATH],
    };
  },
};
