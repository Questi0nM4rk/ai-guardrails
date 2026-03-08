import type { CommandRunner, RunResult } from "@/infra/command-runner";

export class FakeCommandRunner implements CommandRunner {
    readonly calls: string[][] = [];
    private readonly responses = new Map<string, RunResult>();

    register(args: string[], response: RunResult): void {
        this.responses.set(args.join(" "), response);
    }

    async run(
        args: string[],
        _opts?: { cwd?: string; timeout?: number }
    ): Promise<RunResult> {
        this.calls.push(args);
        return (
            this.responses.get(args.join(" ")) ?? {
                stdout: "",
                stderr: "",
                exitCode: 0,
            }
        );
    }
}
