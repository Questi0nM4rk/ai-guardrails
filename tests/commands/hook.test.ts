import { afterEach, beforeEach, describe, expect, mock, test } from "bun:test";
import { runHook } from "@/commands/hook";

let stderrChunks: string[] = [];
let exitCode: number | undefined;
let originalWrite: typeof process.stderr.write;
let originalExit: typeof process.exit;

beforeEach(() => {
  stderrChunks = [];
  exitCode = undefined;
  originalWrite = process.stderr.write.bind(process.stderr);
  originalExit = process.exit.bind(process);
  process.stderr.write = mock((data: string | Uint8Array) => {
    stderrChunks.push(
      typeof data === "string" ? data : Buffer.from(data).toString("utf8")
    );
    return true;
  }) as unknown as typeof process.stderr.write;
  process.exit = mock((code?: number) => {
    exitCode = code ?? 0;
    throw new Error(`__test_exit__:${exitCode}`);
  }) as unknown as typeof process.exit;
});

afterEach(() => {
  process.stderr.write = originalWrite;
  process.exit = originalExit;
});

describe("runHook unknown name", () => {
  test("writes diagnostic to stderr and exits 1", async () => {
    await expect(runHook("not-a-hook", [])).rejects.toThrow(/__test_exit__:1/);
    expect(exitCode).toBe(1);
    const out = stderrChunks.join("");
    expect(out).toContain("Unknown hook: not-a-hook");
    expect(out).toContain("Available hooks:");
    expect(out).toContain("run");
    expect(out).toContain("suppress-comments");
    expect(out).toContain("format-stage");
  });
});
