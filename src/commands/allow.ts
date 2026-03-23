import { join } from "node:path";
import { buildContext } from "@/commands/context";
import { PROJECT_CONFIG_PATH } from "@/models/paths";

/**
 * ai-guardrails allow <rule> <glob> "<reason>"
 *
 * Appends an [[allow]] entry to .ai-guardrails/config.toml.
 */
export async function runAllow(
  projectDir: string,
  rule: string,
  glob: string,
  reason: string
): Promise<void> {
  const ruleRe = /^[\w-]+\/[\w\-.]+$/;
  if (!ruleRe.test(rule)) {
    process.stderr.write(
      `Error: rule must be in the format "linter/RULE_CODE" (e.g. biome/noConsole)\n`
    );
    process.exit(1);
  }

  if (glob.trim() === "") {
    process.stderr.write(`Error: glob must not be empty\n`);
    process.exit(1);
  }

  if (reason.trim() === "") {
    process.stderr.write(`Error: reason must not be empty\n`);
    process.exit(1);
  }

  const ctx = buildContext(projectDir, {});
  const { fileManager, console: cons } = ctx;

  const configPath = join(projectDir, PROJECT_CONFIG_PATH);

  // Append the new [[allow]] block — TOML array-of-tables syntax
  const entry = `\n[[allow]]\nrule = "${rule}"\nglob = "${glob}"\nreason = "${reason}"\n`;

  const exists = await fileManager.exists(configPath);
  if (!exists) {
    await fileManager.mkdir(join(projectDir, ".ai-guardrails"), { parents: true });
    await fileManager.writeText(configPath, entry.trimStart());
  } else {
    await fileManager.appendText(configPath, entry);
  }

  cons.success(`Added allow rule: ${rule} for ${glob}`);
}
