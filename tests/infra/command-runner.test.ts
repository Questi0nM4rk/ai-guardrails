import { describe, expect, test } from "bun:test";
import { FakeCommandRunner } from "../fakes/fake-command-runner";

describe("FakeCommandRunner", () => {
    test("returns registered response for matching args", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["ruff", "check", "."], {
            stdout: "src/foo.py:1:1: E501",
            stderr: "",
            exitCode: 1,
        });
        const result = await runner.run(["ruff", "check", "."]);
        expect(result.stdout).toBe("src/foo.py:1:1: E501");
        expect(result.exitCode).toBe(1);
    });

    test("returns empty success for unregistered args", async () => {
        const runner = new FakeCommandRunner();
        const result = await runner.run(["unknown", "command"]);
        expect(result.stdout).toBe("");
        expect(result.stderr).toBe("");
        expect(result.exitCode).toBe(0);
    });

    test("tracks all calls in order", async () => {
        const runner = new FakeCommandRunner();
        await runner.run(["cmd1"]);
        await runner.run(["cmd2", "arg"]);
        expect(runner.calls).toHaveLength(2);
        expect(runner.calls[0]).toEqual(["cmd1"]);
        expect(runner.calls[1]).toEqual(["cmd2", "arg"]);
    });

    test("can register multiple different commands", async () => {
        const runner = new FakeCommandRunner();
        runner.register(["echo", "a"], { stdout: "a", stderr: "", exitCode: 0 });
        runner.register(["echo", "b"], { stdout: "b", stderr: "", exitCode: 0 });
        const a = await runner.run(["echo", "a"]);
        const b = await runner.run(["echo", "b"]);
        expect(a.stdout).toBe("a");
        expect(b.stdout).toBe("b");
    });
});
