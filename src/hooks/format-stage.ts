import { execSync, spawnSync } from "node:child_process";
import { Glob } from "bun";

const FORMATTERS: Array<{
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
    try {
        spawnSync(cmd, rest, { stdio: "inherit" });
    } catch (err) {
        // Formatter not installed or failed to spawn — lefthook will report exit status.
        // Log the raw error so the cause is visible in hook output.
        const message = err instanceof Error ? err.message : String(err);
        process.stderr.write(`[format-stage] failed to run ${cmd}: ${message}\n`);
    }
}

function getStagedFiles(): string[] {
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
        if (matching.length > 0) tryRun(cmd(matching));
    }
    process.exit(0);
}
