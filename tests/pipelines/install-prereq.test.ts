import { describe, expect, test } from "bun:test";
import { installPipeline } from "@/pipelines/install";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeFileManager } from "../fakes/fake-file-manager";
import { makeBaseCtx } from "../steps/pipeline-shared";

describe("install pipeline — hook-kit prereq gate", () => {
  test("fails fast when hook-kit binary is missing from PATH", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["hook-kit", "--version"], {
      stdout: "",
      stderr: "command not found",
      exitCode: 127,
    });
    const fm = new FakeFileManager();
    const ctx = makeBaseCtx({ commandRunner: runner, fileManager: fm });

    const result = await installPipeline.run(ctx);

    expect(result.status).toBe("error");
    if (result.status === "error") {
      expect(result.message).toContain("hook-kit binary not found");
      expect(result.message).toContain("npm i -g @questi0nm4rk/hook-kit");
    }
    // Pipeline aborted before any init module ran — no files written.
    expect(fm.written.length).toBe(0);
  });

  test("proceeds past the gate when hook-kit reports a version", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["hook-kit", "--version"], {
      stdout: "0.2.0\n",
      stderr: "",
      exitCode: 0,
    });
    const ctx = makeBaseCtx({ commandRunner: runner });

    const result = await installPipeline.run(ctx);

    // We're not asserting end-to-end success (init modules may need other
    // mocks); only that the prereq gate let the pipeline progress past it
    // without an early error mentioning the gate.
    if (result.status === "error") {
      expect(result.message).not.toContain("hook-kit binary not found");
    }
  });
});
