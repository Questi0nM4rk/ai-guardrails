export interface RunResult {
    stdout: string;
    stderr: string;
    exitCode: number;
}

export interface CommandRunner {
    run(args: string[], opts?: { cwd?: string; timeout?: number }): Promise<RunResult>;
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

        const cwd = opts?.cwd;
        const proc =
            cwd !== undefined
                ? Bun.spawn([cmd, ...rest], { cwd, stdout: "pipe", stderr: "pipe" })
                : Bun.spawn([cmd, ...rest], { stdout: "pipe", stderr: "pipe" });

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
