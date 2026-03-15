import { describe, expect, test } from "bun:test";
import { evaluate } from "@/check/engine";
import { buildRuleSet } from "@/check/ruleset";

const ruleset = buildRuleSet({});

describe("protect-reads", () => {
  test("Read .ssh/id_rsa → not allow", async () => {
    const result = await evaluate(
      { type: "read", path: "/home/user/.ssh/id_rsa" },
      ruleset
    );
    expect(result.decision).not.toBe("allow");
  });

  test("Read .gnupg/ → not allow", async () => {
    const result = await evaluate(
      { type: "read", path: "/home/user/.gnupg/secring.gpg" },
      ruleset
    );
    expect(result.decision).not.toBe("allow");
  });

  test("Read README.md → allow", async () => {
    const result = await evaluate({ type: "read", path: "README.md" }, ruleset);
    expect(result.decision).toBe("allow");
  });

  test("Read .env → not allow", async () => {
    const result = await evaluate({ type: "read", path: ".env" }, ruleset);
    expect(result.decision).not.toBe("allow");
  });
});
