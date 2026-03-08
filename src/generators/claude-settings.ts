import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";

interface ClaudeSettings {
  permissions: {
    deny: string[];
  };
}

function renderClaudeSettings(_config: ResolvedConfig): string {
  const settings: ClaudeSettings = {
    permissions: {
      deny: [
        "Bash(git push*)",
        "Bash(git push --force*)",
        "Bash(rm -rf /*)",
        "Bash(sudo rm -rf*)",
        "Bash(chmod -R 777*)",
        "Bash(curl * | bash)",
        "Bash(wget * | bash)",
        "Bash(eval $(*))",
        "Bash(python -c*import os*system*)",
      ],
    },
  };
  return JSON.stringify(settings, null, 2);
}

export const claudeSettingsGenerator: ConfigGenerator = {
  id: "claude-settings",
  configFile: ".claude/settings.json",
  generate(config: ResolvedConfig): string {
    return renderClaudeSettings(config);
  },
};
