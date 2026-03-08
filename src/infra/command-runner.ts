export interface RunResult {
    stdout: string;
    stderr: string;
    exitCode: number;
}

export interface CommandRunner {
    run(args: string[], opts?: { cwd?: string; timeout?: number }): Promise<RunResult>;
}

function spawnOrNull(
    cmd: string,
    rest: string[],
    cwd: string | undefined
): Bun.Subprocess<"ignore", "pipe", "pipe"> | null {
    const opts = { stdout: "pipe" as const, stderr: "pipe" as const };
    try {
        return cwd !== undefined
            ? Bun.spawn([cmd, ...rest], { ...opts, cwd })
            : Bun.spawn([cmd, ...rest], opts);
    } catch {
        return null;
    }
}

export class RealCommandRunner implements CommandRunner {
    async run(
        args: string[],
        opts?: { cwd?: string; timeout?: number }
    ): Promise<RunResult> {
        const [cmd, ...rest] = args;
        if (!cmd) {
            return { stdout: "", stderr: "No command provided", exitCode: 1 };
        }

        const proc = spawnOrNull(cmd, rest, opts?.cwd);
        if (proc === null) {
            return {
                stdout: "",
                stderr: `Executable not found in $PATH: "${cmd}"`,
                exitCode: 127,
            };
        }

        let killTimer: ReturnType<typeof setTimeout> | undefined;
        if (opts?.timeout !== undefined) {
            killTimer = setTimeout(() => {
                proc.kill();
            }, opts.timeout);
        }

        const [stdout, stderr, exitCode] = await Promise.all([
            new Response(proc.stdout).text(),
            new Response(proc.stderr).text(),
            proc.exited,
        ]);

        if (killTimer !== undefined) {
            clearTimeout(killTimer);
        }

        return { stdout, stderr, exitCode };
    }
}
