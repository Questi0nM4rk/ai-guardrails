import { homedir } from "node:os";
import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

const TS_LANGUAGE_SECTION = `\
[[language]]
name = "typescript"
formatter = { command = "biome", args = ["format", "--stdin-file-path", "file.ts"] }
auto-format = true

[[language]]
name = "javascript"
formatter = { command = "biome", args = ["format", "--stdin-file-path", "file.js"] }
auto-format = true
`;

const PYTHON_LANGUAGE_SECTION = `\
[[language]]
name = "python"
formatter = { command = "ruff", args = ["format", "-"] }
auto-format = true
language-servers = ["pylsp"]
`;

export const helixOnSaveModule: InitModule = {
  id: "helix-on-save",
  name: "Helix LSP On-Save",
  description: "Configure Helix LSP for on-save linting via .helix/languages.toml",
  category: "editor",
  defaultEnabled: true,
  disableFlag: "--no-helix",
  dependsOn: ["biome-config", "ruff-config"],

  async detect(ctx: InitContext): Promise<boolean> {
    const hasHelixConfig = await ctx.fileManager.exists(
      join(homedir(), ".config", "helix")
    );
    if (hasHelixConfig) return true;

    const result = await ctx.commandRunner.run(["hx", "--version"], {
      cwd: ctx.projectDir,
    });
    return result.exitCode === 0;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const hasTs = ctx.languages.some((l) => l.id === "typescript");
    const hasPython = ctx.languages.some((l) => l.id === "python");

    const helixDir = join(ctx.projectDir, ".helix");
    const tomlPath = join(helixDir, "languages.toml");

    // Skip if file already exists — helix configs are personal
    const exists = await ctx.fileManager.exists(tomlPath);
    if (exists) {
      return {
        status: "skipped",
        message: ".helix/languages.toml already exists, skipping",
      };
    }

    const sections: string[] = [];
    if (hasTs) sections.push(TS_LANGUAGE_SECTION);
    if (hasPython) sections.push(PYTHON_LANGUAGE_SECTION);

    if (sections.length === 0) {
      return { status: "skipped", message: "No supported languages detected" };
    }

    await ctx.fileManager.mkdir(helixDir, { parents: true });

    const header = "# ai-guardrails: project on-save config for Helix\n";
    const content = header + sections.join("\n");

    await ctx.fileManager.writeText(tomlPath, content);

    return {
      status: "ok",
      message: ".helix/languages.toml written",
      filesCreated: [".helix/languages.toml"],
    };
  },
};
