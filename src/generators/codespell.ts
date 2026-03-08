import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import { makeHashHeader } from "@/utils/hash";

function renderCodespellrc(_config: ResolvedConfig): string {
    const content = `[codespell]
skip = .git,*.lock,*.baseline,node_modules,.venv,venv,dist,build,*/tests/fixtures/*
quiet-level = 2
`;
    const header = makeHashHeader(content);
    return `${header}\n${content}`;
}

export const codespellGenerator: ConfigGenerator = {
    id: "codespell",
    configFile: ".codespellrc",
    generate(config: ResolvedConfig): string {
        return renderCodespellrc(config);
    },
};
