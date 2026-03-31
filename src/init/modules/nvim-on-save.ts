import { homedir } from "node:os";
import { join } from "node:path";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

function buildConformLua(hasTs: boolean, hasPython: boolean): string {
  const ftLines: string[] = [];
  if (hasTs) {
    ftLines.push('    typescript = { "biome" },');
    ftLines.push('    javascript = { "biome" },');
  }
  if (hasPython) {
    ftLines.push('    python = { "ruff_format" },');
  }

  return `\
-- ai-guardrails: project on-save config for conform.nvim
-- Add to your init.lua: require("conform").setup(require(".nvim.conform"))
return {
  formatters_by_ft = {
${ftLines.join("\n")}
  },
  format_on_save = {
    timeout_ms = 500,
    lsp_fallback = true,
  },
}
`;
}

export const nvimOnSaveModule: InitModule = {
  id: "nvim-on-save",
  name: "Neovim On-Save Linting",
  description:
    "Generate .nvim/conform.lua project-local config snippet for conform.nvim",

  category: "editor",
  defaultEnabled: false,
  disableFlag: "--no-nvim",
  dependsOn: ["biome-config", "ruff-config"],

  async detect(ctx: InitContext): Promise<boolean> {
    const hasNvimConfig = await ctx.fileManager.exists(
      join(homedir(), ".config", "nvim")
    );
    if (hasNvimConfig) return true;

    const result = await ctx.commandRunner.run(["nvim", "--version"], {
      cwd: ctx.projectDir,
    });
    return result.exitCode === 0;
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const hasTs = ctx.languages.some((l) => l.id === "typescript");
    const hasPython = ctx.languages.some((l) => l.id === "python");

    const nvimDir = join(ctx.projectDir, ".nvim");
    const luaPath = join(nvimDir, "conform.lua");

    // Skip if file already exists
    const exists = await ctx.fileManager.exists(luaPath);
    if (exists) {
      return {
        status: "skipped",
        message: ".nvim/conform.lua already exists, skipping",
      };
    }

    if (!hasTs && !hasPython) {
      return { status: "skipped", message: "No supported languages detected" };
    }

    await ctx.fileManager.mkdir(nvimDir, { parents: true });

    const content = buildConformLua(hasTs, hasPython);
    await ctx.fileManager.writeText(luaPath, content);

    ctx.console.info("Requires conform.nvim: https://github.com/stevearc/conform.nvim");

    return {
      status: "ok",
      message: ".nvim/conform.lua written",
      filesCreated: [".nvim/conform.lua"],
    };
  },
};
