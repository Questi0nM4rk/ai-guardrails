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

    const cwd = opts?.cwd;
    const proc =
      cwd !== undefined
        ? Bun.spawn([cmd, ...rest], { cwd, stdout: "pipe", stderr: "pipe" })
        : Bun.spawn([cmd, ...rest], { stdout: "pipe", stderr: "pipe" });

    const [stdout, stderr] = await Promise.all([
      new Response(proc.stdout).text(),
      new Response(proc.stderr).text(),
    ]);

    if (opts?.timeout !== undefined) {
      const timeoutPromise = new Promise<number>((_, reject) =>
        setTimeout(() => reject(new Error("Command timed out")), opts.timeout),
      );
      const exitCode = await Promise.race([proc.exited, timeoutPromise]);
      return { stdout, stderr, exitCode };
    }

    const exitCode = await proc.exited;
    return { stdout, stderr, exitCode };
  }
}
