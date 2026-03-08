import { spawnSync } from "node:child_process";
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

async function findFiles(pattern: string, cwd: string): Promise<string[]> {
  const g = new Glob(pattern);
  const results: string[] = [];
  for await (const file of g.scan({ cwd, absolute: true })) {
    results.push(file);
  }
  return results;
}

export async function runFormatStage(): Promise<never> {
  const cwd = process.cwd();
  const discovered = await Promise.all(
    FORMATTERS.map(async ({ glob: pattern, cmd }) => ({
      files: await findFiles(pattern, cwd),
      cmd,
    })),
  );
  for (const { files, cmd } of discovered) {
    if (files.length > 0) tryRun(cmd(files));
  }
  process.exit(0);
}
