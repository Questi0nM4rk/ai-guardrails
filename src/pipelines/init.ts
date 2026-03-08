import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import { PROJECT_CONFIG_PATH } from "@/models/paths";
import type { Pipeline, PipelineContext, PipelineResult } from "@/pipelines/types";
import { installPipeline } from "@/pipelines/install";
import { dirname, join } from "node:path";
import { stringify as stringifyToml } from "smol-toml";

type Profile = "strict" | "standard" | "minimal";

const PROFILES: readonly Profile[] = ["strict", "standard", "minimal"] as const;

function isProfile(value: string): value is Profile {
  return (PROFILES as readonly string[]).includes(value);
}

async function promptProfile(): Promise<Profile> {
  process.stdout.write("Select profile [strict/standard/minimal] (default: standard): ");
  for await (const line of console) {
    const input = line.trim().toLowerCase();
    if (input === "" || isProfile(input)) {
      return (input || "standard") as Profile;
    }
    process.stdout.write("Invalid. Choose strict/standard/minimal: ");
  }
  return "standard";
}

async function promptIgnoreRules(): Promise<string[]> {
  process.stdout.write("Rules to ignore (comma-separated linter/RULE, or press Enter to skip): ");
  for await (const line of console) {
    const input = line.trim();
    if (!input) return [];
    return input
      .split(",")
      .map((r) => r.trim())
      .filter((r) => r.length > 0);
  }
  return [];
}

async function writeProjectConfig(
  projectDir: string,
  profile: Profile,
  ignoreRules: string[],
  fileManager: FileManager,
): Promise<void> {
  const dest = join(projectDir, PROJECT_CONFIG_PATH);
  await fileManager.mkdir(dirname(dest), { parents: true });

  const ignoreEntries = ignoreRules.map((rule) => ({
    rule,
    reason: "user-configured at init",
  }));

  const configData: Record<string, unknown> = { profile, ignore: ignoreEntries };
  await fileManager.writeText(dest, stringifyToml(configData));
}

async function checkConfigExists(projectDir: string, fileManager: FileManager): Promise<boolean> {
  try {
    await fileManager.readText(join(projectDir, PROJECT_CONFIG_PATH));
    return true;
  } catch {
    return false;
  }
}

function logInitStart(cons: Console, interactive: boolean): void {
  if (interactive) {
    cons.info("Running interactive init...");
  } else {
    cons.info("Running non-interactive init with defaults...");
  }
}

export const initPipeline: Pipeline = {
  async run(ctx: PipelineContext): Promise<PipelineResult> {
    const { projectDir, fileManager, console: cons } = ctx;

    const force = ctx.flags.force === true;
    const upgrade = ctx.flags.upgrade === true;

    const configExists = await checkConfigExists(projectDir, fileManager);
    if (configExists && !force && !upgrade) {
      return {
        status: "error",
        message:
          ".ai-guardrails/config.toml already exists. Use --force to overwrite or --upgrade to refresh.",
      };
    }

    const isInteractive = process.stdin.isTTY === true;
    logInitStart(cons, isInteractive);

    let profile: Profile = "standard";
    let ignoreRules: string[] = [];

    if (isInteractive) {
      profile = await promptProfile();
      ignoreRules = await promptIgnoreRules();
    } else {
      const flagProfile = ctx.flags.profile;
      if (typeof flagProfile === "string" && isProfile(flagProfile)) {
        profile = flagProfile;
      }
    }

    cons.step(`Writing config: profile=${profile}...`);
    await writeProjectConfig(projectDir, profile, ignoreRules, fileManager);
    cons.success("Config written to .ai-guardrails/config.toml");

    return installPipeline.run(ctx);
  },
};
