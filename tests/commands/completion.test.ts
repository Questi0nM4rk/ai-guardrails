import { describe, expect, test } from "bun:test";
import {
  generateBashCompletion,
  generateFishCompletion,
  generateZshCompletion,
  runCompletion,
} from "@/commands/completion";

const ALL_COMMANDS = [
  "init",
  "install",
  "generate",
  "check",
  "snapshot",
  "status",
  "report",
  "hook",
  "completion",
];

describe("generateBashCompletion", () => {
  test("contains complete -F registration", () => {
    const out = generateBashCompletion();
    expect(out).toContain("complete -F _ai_guardrails ai-guardrails");
  });

  test("contains all command names", () => {
    const out = generateBashCompletion();
    for (const cmd of ALL_COMMANDS) {
      expect(out).toContain(cmd);
    }
  });

  test("contains init-specific flags", () => {
    const out = generateBashCompletion();
    expect(out).toContain("--yes");
    expect(out).toContain("--profile");
    expect(out).toContain("--no-hooks");
    expect(out).toContain("--config-strategy");
  });

  test("contains check-specific flags", () => {
    const out = generateBashCompletion();
    expect(out).toContain("--format");
    expect(out).toContain("--baseline");
    expect(out).toContain("--strict");
  });
});

describe("generateZshCompletion", () => {
  test("starts with #compdef", () => {
    const out = generateZshCompletion();
    expect(out).toContain("#compdef ai-guardrails");
  });

  test("contains all command names", () => {
    const out = generateZshCompletion();
    for (const cmd of ALL_COMMANDS) {
      expect(out).toContain(cmd);
    }
  });

  test("contains _describe usage", () => {
    const out = generateZshCompletion();
    expect(out).toContain("_describe");
  });

  test("contains _arguments for per-command completions", () => {
    const out = generateZshCompletion();
    expect(out).toContain("_arguments");
  });

  test("contains init-specific flags", () => {
    const out = generateZshCompletion();
    expect(out).toContain("--yes");
    expect(out).toContain("--profile");
    expect(out).toContain("--config-strategy");
  });

  test("contains check-specific flags", () => {
    const out = generateZshCompletion();
    expect(out).toContain("--format");
    expect(out).toContain("--strict");
  });
});

describe("generateFishCompletion", () => {
  test("contains complete -c ai-guardrails", () => {
    const out = generateFishCompletion();
    expect(out).toContain("complete -c ai-guardrails");
  });

  test("contains all command names", () => {
    const out = generateFishCompletion();
    for (const cmd of ALL_COMMANDS) {
      expect(out).toContain(cmd);
    }
  });

  test("contains __fish_use_subcommand guards", () => {
    const out = generateFishCompletion();
    expect(out).toContain("__fish_use_subcommand");
  });

  test("contains __fish_seen_subcommand_from guards", () => {
    const out = generateFishCompletion();
    expect(out).toContain("__fish_seen_subcommand_from");
  });

  test("contains init-specific flags", () => {
    const out = generateFishCompletion();
    // fish uses -l <name> syntax (long flag without --)
    expect(out).toContain("-l yes");
    expect(out).toContain("-l profile");
    expect(out).toContain("-l config-strategy");
  });

  test("contains check-specific flags", () => {
    const out = generateFishCompletion();
    expect(out).toContain("-l format");
    expect(out).toContain("-l strict");
  });
});

describe("runCompletion unknown shell", () => {
  test("writes error message and calls process.exit(1) for unknown shell", () => {
    const stderrChunks: string[] = [];
    const originalStderr = process.stderr.write.bind(process.stderr);
    process.stderr.write = (chunk: string | Uint8Array): boolean => {
      stderrChunks.push(
        typeof chunk === "string" ? chunk : new TextDecoder().decode(chunk)
      );
      return true;
    };

    let capturedExitCode: number | undefined;
    const originalExit = process.exit;
    process.exit = ((_code?: number) => {
      capturedExitCode = _code;
    }) as unknown as typeof process.exit;

    try {
      runCompletion("powershell");
    } finally {
      process.stderr.write = originalStderr;
      process.exit = originalExit;
    }

    const errOutput = stderrChunks.join("");
    expect(errOutput).toContain("powershell");
    expect(errOutput).toContain("bash, zsh, or fish");
    expect(capturedExitCode).toBe(1);
  });
});
