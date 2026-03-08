import { execSync, spawnSync } from "node:child_process";
import { Glob } from "bun";

export const FORMATTERS: Array<{
    glob: string;
    cmd: (files: string[]) => string[];
}> = [
    { glob: "**/*.py", cmd: (f) => ["ruff", "format", ...f] },
    { glob: "**/*.{ts,tsx,js,jsx}", cmd: (f) => ["biome", "format", "--write", ...f] },
    { glob: "**/*.rs", cmd: (f) => ["rustfmt", ...f] },
    { glob: "**/*.go", cmd: (f) => ["gofmt", "-w", ...f] },
    { glob: "**/*.lua", cmd: (f) => ["stylua", ...f] },
    { glob: "**/*.{c,cpp,cc,h,hpp}", cmd: (f) => ["clang-format", "-i", ...f] },
];

function tryRun(args: string[]): void {
    const [cmd, ...rest] = args;
    if (!cmd) return;
    const result = spawnSync(cmd, rest, { stdio: "inherit" });
    if (result.error) {
        // Formatter not installed or failed to spawn — lefthook will report exit status.
        // Log the raw error so the cause is visible in hook output.
        process.stderr.write(
            `[format-stage] failed to run ${cmd}: ${result.error.message}\n`
        );
    }
}

export function getStagedFiles(): string[] {
    try {
        const output = execSync("git diff --cached --name-only", { encoding: "utf8" });
        return output.split("\n").filter(Boolean);
    } catch {
        return [];
    }
}

export async function runFormatStage(): Promise<never> {
    const cwd = process.cwd();
    const stagedFiles = getStagedFiles().map((f) => `${cwd}/${f}`);
    if (stagedFiles.length === 0) process.exit(0);

    for (const { glob: pattern, cmd } of FORMATTERS) {
        const g = new Glob(pattern);
        const matching = stagedFiles.filter((f) => g.match(f));
        if (matching.length > 0) {
            tryRun(cmd(matching));
            // Re-stage formatted files so the commit contains the formatted code.
            spawnSync("git", ["add", ...matching], { stdio: "inherit" });
        }
    }
    process.exit(0);
}
