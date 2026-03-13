import type { DetectOptions, LanguagePlugin } from "@/languages/types";
import { codespellRunner } from "@/runners/codespell";
import { markdownlintRunner } from "@/runners/markdownlint";
import type { LinterRunner } from "@/runners/types";

export const universalPlugin: LanguagePlugin = {
  id: "universal",
  name: "Universal",

  /** Universal plugin is always active */
  async detect(_opts: DetectOptions): Promise<boolean> {
    return true;
  },

  runners(): LinterRunner[] {
    return [codespellRunner, markdownlintRunner];
  },
};
