import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import { DANGEROUS_DENY_GLOBS } from "@/hooks/dangerous-patterns";
import { withJsoncHashHeader } from "@/utils/hash";

interface ClaudeSettings {
    permissions: {
        deny: string[];
    };
}

function renderClaudeSettings(_config: ResolvedConfig): string {
    const settings: ClaudeSettings = {
        permissions: {
            deny: DANGEROUS_DENY_GLOBS,
        },
    };
    return JSON.stringify(settings, null, 2);
}

export const claudeSettingsGenerator: ConfigGenerator = {
    id: "claude-settings",
    configFile: ".claude/settings.json",
    generate(config: ResolvedConfig): string {
        return withJsoncHashHeader(renderClaudeSettings(config));
    },
};
