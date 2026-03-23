import { Command, Option } from "@commander-js/extra-typings";
import { runAllow } from "@/commands/allow";
import { runCheck } from "@/commands/check";
import { getCompletionScript } from "@/commands/completion";
import { runGenerate } from "@/commands/generate";
import { runHook } from "@/commands/hook";
import { runInit } from "@/commands/init";
import { runInstall } from "@/commands/install";
import { runQuery } from "@/commands/query";
import { runReport } from "@/commands/report";
import { runSnapshot } from "@/commands/snapshot";
import { runStatus } from "@/commands/status";
import pkg from "../package.json";

const program = new Command()
  .name("ai-guardrails")
  .description("Pedantic code quality enforcement for AI-maintained repositories")
  .version(pkg.version);

// ---------------------------------------------------------------------------
// Global options (inherited by subcommands via .optsWithGlobals())
// ---------------------------------------------------------------------------
program
  .option("--project-dir <dir>", "Override working directory", process.cwd())
  .option("--quiet", "Suppress info/success output")
  .option("--no-color", "Disable ANSI color output");

function getProjectDir(): string {
  const projectDir: unknown = program.getOptionValue("projectDir");
  return typeof projectDir === "string" ? projectDir : process.cwd();
}

// ---------------------------------------------------------------------------
// install
// ---------------------------------------------------------------------------
program
  .command("install")
  .description("One-time machine setup")
  .option("--upgrade", "Overwrite existing machine config")
  .action(async (opts) => {
    await runInstall(getProjectDir(), { ...opts });
  });

// ---------------------------------------------------------------------------
// init
// ---------------------------------------------------------------------------
program
  .command("init")
  .description("Per-project setup")
  .option("--profile <profile>", "Profile: strict | standard | minimal")
  .option("--force", "Overwrite existing managed files")
  .option("--upgrade", "Refresh all generated files, preserve config.toml")
  .option("--yes", "Accept all defaults (non-interactive)")
  .option("--no-hooks", "Skip lefthook install")
  .option("--no-ci", "Skip CI workflow generation")
  .option("--no-agent-rules", "Skip AGENTS.md and IDE rule files")
  .option("--no-baseline", "Skip baseline snapshot")
  .option("--no-editorconfig", "Skip .editorconfig generation")
  .option("--no-markdownlint", "Skip .markdownlint.jsonc generation")
  .option("--no-codespell", "Skip .codespellrc generation")
  .option("--no-ruff", "Skip ruff.toml generation")
  .option("--no-biome", "Skip biome.jsonc generation")
  .option("--no-agent-hooks", "Skip .claude/settings.json generation")
  .option("--interactive", "Prompt for each optional step")
  .addOption(
    new Option("--config-strategy <strategy>", "How to handle existing lang configs")
      .choices(["merge", "replace", "skip"])
      .default("merge")
  )
  .action(async (opts) => {
    await runInit(getProjectDir(), { ...opts });
  });

// ---------------------------------------------------------------------------
// generate
// ---------------------------------------------------------------------------
program
  .command("generate")
  .description("Regenerate all managed config files")
  .option("--check", "Verify files are up-to-date (CI mode)")
  .action(async (opts) => {
    await runGenerate(getProjectDir(), { ...opts });
  });

// ---------------------------------------------------------------------------
// check
// ---------------------------------------------------------------------------
program
  .command("check")
  .description("Hold-the-line enforcement: fail if new issues found")
  .option("--baseline <path>", "Custom baseline path")
  .option("--format <format>", "Output format: text | sarif", "text")
  .option("--strict", "Ignore baseline — all issues are new")
  .action(async (opts) => {
    await runCheck(getProjectDir(), { ...opts });
  });

// ---------------------------------------------------------------------------
// snapshot
// ---------------------------------------------------------------------------
program
  .command("snapshot")
  .description("Capture current lint state as baseline")
  .option("--baseline <path>", "Custom output path")
  .action(async (opts) => {
    await runSnapshot(getProjectDir(), { ...opts });
  });

// ---------------------------------------------------------------------------
// status
// ---------------------------------------------------------------------------
program
  .command("status")
  .description("Project health dashboard")
  .action(async () => {
    await runStatus(getProjectDir(), {});
  });

// ---------------------------------------------------------------------------
// report
// ---------------------------------------------------------------------------
program
  .command("report")
  .description("Show recent check run history")
  .option("--last <n>", "Number of runs to show", (v) => Number.parseInt(v, 10), 10)
  .action(async (opts) => {
    await runReport(getProjectDir(), { last: opts.last });
  });

// ---------------------------------------------------------------------------
// hook (internal dispatcher)
// ---------------------------------------------------------------------------
program
  .command("hook")
  .description("Internal hook dispatcher (invoked by lefthook / Claude Code)")
  .argument(
    "<hook-name>",
    "Hook to run: dangerous-cmd | protect-configs | suppress-comments | format-stage"
  )
  .argument("[args...]", "Additional arguments (e.g. staged file paths)")
  .action(async (hookName, args) => {
    await runHook(hookName, args);
  });

// ---------------------------------------------------------------------------
// allow
// ---------------------------------------------------------------------------
program
  .command("allow")
  .description("Add an inline allow rule to .ai-guardrails/config.toml")
  .argument("<rule>", "Rule in linter/RULE_CODE format (e.g. biome/noConsole)")
  .argument("<glob>", "File glob to apply the rule to (e.g. src/**/*.ts)")
  .argument("<reason>", "Human-readable reason for allowing the rule")
  .action(async (rule, glob, reason) => {
    await runAllow(getProjectDir(), rule, glob, reason);
  });

// ---------------------------------------------------------------------------
// query
// ---------------------------------------------------------------------------
program
  .command("query")
  .description("Show all files where a rule is allowed (config + inline comments)")
  .argument("<rule>", "Rule in linter/RULE_CODE format (e.g. biome/noConsole)")
  .action(async (rule) => {
    await runQuery(getProjectDir(), rule);
  });

// ---------------------------------------------------------------------------
// completion
// ---------------------------------------------------------------------------
program
  .command("completion")
  .description("Generate shell completion script")
  .argument("<shell>", "Shell: bash | zsh | fish")
  .action((shell) => {
    try {
      process.stdout.write(getCompletionScript(shell));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      process.stderr.write(`${msg}\n`);
      process.exit(1);
    }
  });

program.parseAsync(process.argv).catch((err: unknown) => {
  const msg = err instanceof Error ? err.message : String(err);
  process.stderr.write(`Fatal: ${msg}\n`);
  process.exit(2);
});
