import { describe, expect, test } from "bun:test";
import { getCompletionScript } from "@/commands/completion";
import { generateBashCompletion } from "@/utils/completion-bash";
import { generateFishCompletion } from "@/utils/completion-fish";
import { generateZshCompletion } from "@/utils/completion-zsh";

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

describe("getCompletionScript", () => {
  test("returns bash completion for bash shell", () => {
    const script = getCompletionScript("bash");
    expect(script).toContain("complete -F _ai_guardrails ai-guardrails");
  });

  test("returns zsh completion for zsh shell", () => {
    const script = getCompletionScript("zsh");
    expect(script).toContain("#compdef ai-guardrails");
  });

  test("returns fish completion for fish shell", () => {
    const script = getCompletionScript("fish");
    expect(script).toContain("complete -c ai-guardrails");
  });

  test("throws for unknown shell", () => {
    expect(() => getCompletionScript("powershell")).toThrow(
      "Unknown shell: powershell. Use bash, zsh, or fish."
    );
  });
});
