import { describe, expect, test } from "bun:test";
import { checkHookKitStep } from "@/steps/check-hook-kit";
import { FakeCommandRunner } from "../fakes/fake-command-runner";

describe("checkHookKitStep", () => {
  test("returns ok with version when hook-kit is on PATH", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["hook-kit", "--version"], {
      stdout: "0.1.0\n",
      stderr: "",
      exitCode: 0,
    });
    const result = await checkHookKitStep(runner);
    expect(result.status).toBe("ok");
    if (result.status === "ok") {
      expect(result.message).toContain("0.1.0");
    }
  });

  test("returns ok with 'unknown' when hook-kit prints empty version", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["hook-kit", "--version"], {
      stdout: "",
      stderr: "",
      exitCode: 0,
    });
    const result = await checkHookKitStep(runner);
    expect(result.status).toBe("ok");
    if (result.status === "ok") {
      expect(result.message).toContain("unknown");
    }
  });

  test("returns error with install hint when hook-kit is missing", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["hook-kit", "--version"], {
      stdout: "",
      stderr: "",
      exitCode: 127,
    });
    const result = await checkHookKitStep(runner);
    expect(result.status).toBe("error");
    if (result.status === "error") {
      expect(result.message).toContain("hook-kit binary not found");
      expect(result.message).toContain("npm i -g @questi0nm4rk/hook-kit");
    }
  });
});
