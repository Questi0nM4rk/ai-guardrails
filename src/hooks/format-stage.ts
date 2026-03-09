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

function tryRun(args: string[]): boolean {
    const [cmd, ...rest] = args;
    if (!cmd) return false;
    const result = spawnSync(cmd, rest, { stdio: "inherit" });
    if (result.error) {
        // Formatter not installed or failed to spawn — lefthook will report exit status.
        // Log the raw error so the cause is visible in hook output.
        process.stderr.write(
            `[format-stage] failed to run ${cmd}: ${result.error.message}\n`
        );
        return false;
    }
    if (result.status !== 0) {
        process.stderr.write(
            `[format-stage] ${cmd} exited with status ${String(result.status)}\n`
        );
        return false;
    }
    return true;
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
            const ok = tryRun(cmd(matching));
            // Re-stage formatted files so the commit contains the formatted code.
            // Only re-stage if the formatter succeeded — failed runs leave the staged
            // version intact, which is safer than staging potentially half-formatted files.
            if (ok && !tryRun(["git", "add", ...matching])) {
                process.exit(1);
            }
        }
    }
    process.exit(0);
}
