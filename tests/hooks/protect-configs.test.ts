import { describe, expect, test } from "bun:test";
import { evaluate } from "@/check/engine";
import { buildRuleSet } from "@/check/ruleset";

const ruleset = buildRuleSet({});

describe("protect-configs — write events", () => {
  test("Edit .env path → not allow", async () => {
    const result = await evaluate({ type: "write", path: ".env" }, ruleset);
    expect(result.decision).not.toBe("allow");
  });

  test("Write biome.jsonc → not allow", async () => {
    const result = await evaluate({ type: "write", path: "biome.jsonc" }, ruleset);
    expect(result.decision).not.toBe("allow");
  });

  test("Write .claude/settings.json → not allow", async () => {
    const result = await evaluate(
      { type: "write", path: ".claude/settings.json" },
      ruleset
    );
    expect(result.decision).not.toBe("allow");
  });

  test("Write src/main.ts → allow", async () => {
    const result = await evaluate({ type: "write", path: "src/main.ts" }, ruleset);
    expect(result.decision).toBe("allow");
  });

  test("Write package.json → not allow", async () => {
    const result = await evaluate({ type: "write", path: "package.json" }, ruleset);
    expect(result.decision).not.toBe("allow");
  });
});

describe("protect-configs — Bash redirect", () => {
  test("Bash redirect to .env → not allow", async () => {
    const result = await evaluate(
      { type: "bash", command: "cat secret > .env" },
      ruleset
    );
    expect(result.decision).not.toBe("allow");
  });

  test("Bash safe command → allow", async () => {
    const result = await evaluate({ type: "bash", command: "echo hello" }, ruleset);
    expect(result.decision).toBe("allow");
  });
});
