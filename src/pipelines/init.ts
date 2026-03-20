import { dirname, join } from "node:path";
import { createInterface } from "node:readline";
import { stringify as stringifyToml } from "smol-toml";
import { PROFILES, type Profile } from "@/config/schema";
import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import { PROJECT_CONFIG_PATH } from "@/models/paths";
import { installPipeline } from "@/pipelines/install";
import type { Pipeline, PipelineContext, PipelineResult } from "@/pipelines/types";
import { checkPrerequisites } from "@/steps/check-prerequisites";
import { detectLanguagesStep } from "@/steps/detect-languages";
import { installPrerequisites } from "@/steps/install-prerequisites";

function isProfile(value: string): value is Profile {
  return PROFILES.some((p) => p === value);
}

function createStdinReader(): ReturnType<typeof createInterface> {
  return createInterface({ input: process.stdin, output: process.stdout });
}

async function askQuestion(
  rl: ReturnType<typeof createInterface>,
  question: string
): Promise<string> {
  return new Promise((resolve) => {
    rl.question(question, resolve);
  });
}

async function promptProfile(): Promise<Profile> {
  const rl = createStdinReader();
  try {
    let prompt = "Select profile [strict/standard/minimal] (default: standard): ";
    for (;;) {
      const input = await askQuestion(rl, prompt);
      const trimmed = input.trim().toLowerCase();
      if (trimmed === "") return "standard";
      if (isProfile(trimmed)) return trimmed;
      prompt = "Invalid. Choose strict/standard/minimal (default: standard): ";
    }
  } finally {
    rl.close();
  }
}

async function promptIgnoreRules(): Promise<string[]> {
  const rl = createStdinReader();
  try {
    const input = await askQuestion(
      rl,
      "Rules to ignore (comma-separated linter/RULE, or press Enter to skip): "
    );
    const trimmed = input.trim();
    if (!trimmed) return [];
    return trimmed
      .split(",")
      .map((r) => r.trim())
      .filter((r) => r.length > 0);
  } finally {
    rl.close();
  }
}

async function writeProjectConfig(
  projectDir: string,
  profile: Profile,
  ignoreRules: string[],
  fileManager: FileManager
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

async function checkConfigExists(
  projectDir: string,
  fileManager: FileManager
): Promise<boolean> {
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
    const { projectDir, fileManager, commandRunner, console: cons } = ctx;

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

    const isInteractive =
      process.stdin.isTTY === true || ctx.flags.interactive === true;
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

    cons.step("Detecting languages...");
    const { result: detectResult, languages } = await detectLanguagesStep(
      projectDir,
      fileManager
    );
    if (detectResult.status === "error") {
      return { status: "error", message: detectResult.message };
    }
    cons.success(detectResult.message);

    cons.step("Checking prerequisites...");
    const { report } = await checkPrerequisites(cons, commandRunner, languages);

    await installPrerequisites(cons, commandRunner, report, projectDir, isInteractive);

    return installPipeline.run(ctx);
  },
};
