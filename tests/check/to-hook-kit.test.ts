import { describe, expect, test } from "bun:test";
import {
  buildAllModules,
  CC_TOOL,
  fromHookKit,
  synthesizeHookEvent,
  toCommandModule,
  toPathModules,
} from "@/check/to-hook-kit";
import type { CommandRule, PathRule, RuleSet } from "@/check/types";

const LABEL = "[t]";

describe("synthesizeHookEvent", () => {
  test("bash → toolName Bash, toolInput.command", () => {
    const e = synthesizeHookEvent({ type: "bash", command: "ls -la" }, "s1");
    expect(e.eventName).toBe("PreToolUse");
    expect(e.toolName).toBe(CC_TOOL.BASH);
    expect(e.toolInput).toEqual({ command: "ls -la" });
    expect(e.sessionId).toBe("s1");
  });

  test("write → toolName Write, toolInput.file_path", () => {
    const e = synthesizeHookEvent({ type: "write", path: "/tmp/x" }, "s2");
    expect(e.toolName).toBe(CC_TOOL.WRITE);
    expect(e.toolInput).toEqual({ file_path: "/tmp/x" });
  });

  test("read → toolName Read, toolInput.file_path", () => {
    const e = synthesizeHookEvent({ type: "read", path: "/tmp/y" }, "s3");
    expect(e.toolName).toBe(CC_TOOL.READ);
    expect(e.toolInput).toEqual({ file_path: "/tmp/y" });
  });
});

describe("fromHookKit", () => {
  test("null → allow", () => {
    expect(fromHookKit(null)).toEqual({ decision: "allow" });
  });

  test("deny → deny with reason", () => {
    const r = fromHookKit({ kind: "deny", reason: "no" });
    expect(r).toEqual({ decision: "deny", reason: "no" });
  });

  test("escalate → ask with reason", () => {
    const r = fromHookKit({ kind: "escalate", reason: "maybe" });
    expect(r).toEqual({ decision: "ask", reason: "maybe" });
  });

  test("context → allow (informational, doesn't gate the tool call)", () => {
    const r = fromHookKit({ kind: "context", message: "fyi" });
    expect(r).toEqual({ decision: "allow" });
  });
});

describe("toCommandModule", () => {
  test("returns one Bash module with the rules translated", () => {
    const rules: CommandRule[] = [
      { kind: "call", cmd: "rm", flags: ["-rf"], decision: "deny", reason: "rm -rf" },
    ];
    const mod = toCommandModule(rules, LABEL);
    expect(mod.id).toBe("ai-guardrails-bash");
    expect(mod.events).toEqual(["PreToolUse"]);
    expect(mod.matchers).toEqual([CC_TOOL.BASH]);
    expect(mod.rules.length).toBe(1);
  });

  test("ignores unknown rule kinds rather than throwing", () => {
    const mod = toCommandModule([], LABEL);
    expect(mod.rules.length).toBe(0);
  });
});

describe("toPathModules", () => {
  test("write rule produces write module + redirect module", () => {
    const rules: PathRule[] = [
      {
        kind: "path",
        event: "write",
        pattern: /\.env$/,
        decision: "deny",
        reason: ".env write",
      },
    ];
    const mods = toPathModules(rules, LABEL);
    expect(mods.map((m) => m.id).sort()).toEqual([
      "ai-guardrails-paths-write",
      "ai-guardrails-redirects",
    ]);
    const write = mods.find((m) => m.id === "ai-guardrails-paths-write");
    expect(write?.matchers).toEqual([
      CC_TOOL.EDIT,
      CC_TOOL.WRITE,
      CC_TOOL.NOTEBOOK_EDIT,
    ]);
    const red = mods.find((m) => m.id === "ai-guardrails-redirects");
    expect(red?.matchers).toEqual([CC_TOOL.BASH]);
  });

  test("read rule produces only the read module", () => {
    const rules: PathRule[] = [
      {
        kind: "path",
        event: "read",
        pattern: /\/.ssh\//,
        decision: "ask",
        reason: ".ssh read",
      },
    ];
    const mods = toPathModules(rules, LABEL);
    expect(mods.map((m) => m.id)).toEqual(["ai-guardrails-paths-read"]);
    expect(mods[0]?.matchers).toEqual([CC_TOOL.READ]);
  });

  test("event=both produces write + read + redirect modules", () => {
    const rules: PathRule[] = [
      {
        kind: "path",
        event: "both",
        pattern: /secret/,
        decision: "ask",
        reason: "secret",
      },
    ];
    const mods = toPathModules(rules, LABEL);
    expect(mods.map((m) => m.id).sort()).toEqual([
      "ai-guardrails-paths-read",
      "ai-guardrails-paths-write",
      "ai-guardrails-redirects",
    ]);
  });

  test("empty rules produces no modules", () => {
    expect(toPathModules([], LABEL)).toEqual([]);
  });
});

describe("buildAllModules", () => {
  test("composes the command module and the path modules", () => {
    const ruleset: RuleSet = {
      commandRules: [{ kind: "call", cmd: "rm", decision: "deny", reason: "x" }],
      pathRules: [
        {
          kind: "path",
          event: "write",
          pattern: /\.env$/,
          decision: "deny",
          reason: "y",
        },
      ],
    };
    const mods = buildAllModules(ruleset, LABEL);
    const ids = mods.map((m) => m.id).sort();
    expect(ids).toEqual([
      "ai-guardrails-bash",
      "ai-guardrails-paths-write",
      "ai-guardrails-redirects",
    ]);
  });
});
