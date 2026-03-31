import { agentRulesModule } from "@/init/modules/agent-rules";
import { baselineModule } from "@/init/modules/baseline";
import { biomeConfigModule } from "@/init/modules/biome-config";
import { claudeSettingsModule } from "@/init/modules/claude-settings";
import { codespellConfigModule } from "@/init/modules/codespell-config";
import { configTuningModule } from "@/init/modules/config-tuning";
import { editorconfigModule } from "@/init/modules/editorconfig";
import { githubActionsModule } from "@/init/modules/github-actions";
import { githubBranchProtectionModule } from "@/init/modules/github-branch-protection";
import { githubCcReviewerModule } from "@/init/modules/github-cc-reviewer";
import { githubPrTemplateModule } from "@/init/modules/github-pr-template";
import { githubProtectedPatternsModule } from "@/init/modules/github-protected-patterns";
import { helixOnSaveModule } from "@/init/modules/helix-on-save";
import { lefthookModule } from "@/init/modules/lefthook";
import { markdownlintConfigModule } from "@/init/modules/markdownlint-config";
import { nvimOnSaveModule } from "@/init/modules/nvim-on-save";
import { profileSelectionModule } from "@/init/modules/profile-selection";
import { ruffConfigModule } from "@/init/modules/ruff-config";
import { staticcheckConfigModule } from "@/init/modules/staticcheck-config";
import { toolInstallModule } from "@/init/modules/tool-install";
import { versionPinModule } from "@/init/modules/version-pin";
import { vscodeOnSaveModule } from "@/init/modules/vscode-on-save";
import { zedOnSaveModule } from "@/init/modules/zed-on-save";
import type { InitModule } from "@/init/types";

export const ALL_INIT_MODULES: readonly InitModule[] = [
  // Original modules (v3.1)
  profileSelectionModule,
  versionPinModule,
  configTuningModule,
  ruffConfigModule,
  staticcheckConfigModule,
  biomeConfigModule,
  editorconfigModule,
  markdownlintConfigModule,
  codespellConfigModule,
  lefthookModule,
  claudeSettingsModule,
  agentRulesModule,
  githubActionsModule,
  toolInstallModule,
  baselineModule,

  // New modules (v3.2)
  githubBranchProtectionModule,
  githubProtectedPatternsModule,
  githubCcReviewerModule,
  githubPrTemplateModule,
  vscodeOnSaveModule,
  helixOnSaveModule,
  nvimOnSaveModule,
  zedOnSaveModule,
];
