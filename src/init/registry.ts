import { agentRulesModule } from "@/init/modules/agent-rules";
import { baselineModule } from "@/init/modules/baseline";
import { biomeConfigModule } from "@/init/modules/biome-config";
import { claudeSettingsModule } from "@/init/modules/claude-settings";
import { codespellConfigModule } from "@/init/modules/codespell-config";
import { configTuningModule } from "@/init/modules/config-tuning";
import { editorconfigModule } from "@/init/modules/editorconfig";
import { githubActionsModule } from "@/init/modules/github-actions";
import { lefthookModule } from "@/init/modules/lefthook";
import { markdownlintConfigModule } from "@/init/modules/markdownlint-config";
import { profileSelectionModule } from "@/init/modules/profile-selection";
import { ruffConfigModule } from "@/init/modules/ruff-config";
import { toolInstallModule } from "@/init/modules/tool-install";
import type { InitModule } from "@/init/types";

export const ALL_INIT_MODULES: readonly InitModule[] = [
  profileSelectionModule,
  configTuningModule,
  ruffConfigModule,
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
];
