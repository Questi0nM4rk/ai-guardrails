import { join } from "node:path";
import { buildContext } from "@/commands/context";
import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import { PROJECT_CONFIG_PATH } from "@/models/paths";

/**
 * Escape a value for use inside a TOML basic string (double-quoted).
 * TOML basic strings only require `\` and `"` to be escaped.
 */
export function escapeTOMLString(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

/**
 * Core logic for appending an [[allow]] entry — injectable for testing.
 */
export async function appendAllowEntry(
  projectDir: string,
  rule: string,
  glob: string,
  reason: string,
  fileManager: FileManager,
  cons: Console
): Promise<void> {
  const configPath = join(projectDir, PROJECT_CONFIG_PATH);

  // Append the new [[allow]] block — TOML array-of-tables syntax.
  // Escape backslashes and double-quotes so values are safe inside TOML
  // basic strings (double-quoted), per the TOML v1.0 spec §2.4.
  const entry = `\n[[allow]]\nrule = "${rule}"\nglob = "${escapeTOMLString(glob)}"\nreason = "${escapeTOMLString(reason)}"\n`;

  const exists = await fileManager.exists(configPath);
  if (!exists) {
    await fileManager.mkdir(join(projectDir, ".ai-guardrails"), { parents: true });
    await fileManager.writeText(configPath, entry.trimStart());
  } else {
    await fileManager.appendText(configPath, entry);
  }

  cons.success(`Added allow rule: ${rule} for ${glob}`);
}

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
  await appendAllowEntry(projectDir, rule, glob, reason, ctx.fileManager, ctx.console);
}
