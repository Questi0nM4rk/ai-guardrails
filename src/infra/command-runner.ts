export interface RunResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

export interface CommandRunner {
  run(args: string[], opts?: { cwd?: string; timeout?: number }): Promise<RunResult>;
}

export class RealCommandRunner implements CommandRunner {
  async run(args: string[], opts?: { cwd?: string; timeout?: number }): Promise<RunResult> {
    const [cmd, ...rest] = args;
    if (!cmd) {
      return { stdout: "", stderr: "No command provided", exitCode: 1 };
    }

    const proc =
      opts?.cwd !== undefined
        ? Bun.spawn([cmd, ...rest], { cwd: opts.cwd, stdout: "pipe", stderr: "pipe" })
        : Bun.spawn([cmd, ...rest], { stdout: "pipe", stderr: "pipe" });

    const execute = async (): Promise<RunResult> => {
      const [stdout, stderr] = await Promise.all([
        new Response(proc.stdout).text(),
        new Response(proc.stderr).text(),
      ]);
      const exitCode = await proc.exited;
      return { stdout, stderr, exitCode };
    };

    if (opts?.timeout !== undefined) {
      const timeout = opts.timeout;
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => {
          proc.kill();
          reject(new Error(`Command timed out after ${timeout}ms: ${args.join(" ")}`));
        }, timeout),
      );
      return Promise.race([execute(), timeoutPromise]);
    }

    return execute();
  }
}
