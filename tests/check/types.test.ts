import { describe, expect, test } from "bun:test";
import { callRule, pipeRule, recurseRule, redirectRule } from "@/check/builder-cmd";
import { protectRead, protectWrite } from "@/check/builder-path";

describe("callRule", () => {
  test("returns correct kind and defaults", () => {
    const r = callRule("rm", { flags: ["-r", "-f"], reason: "test" });
    expect(r.kind).toBe("call");
    expect(r.cmd).toBe("rm");
    expect(r.flags).toEqual(["-r", "-f"]);
    expect(r.decision).toBe("ask");
  });

  test("accepts explicit decision", () => {
    const r = callRule("rm", { decision: "deny", reason: "test" });
    expect(r.decision).toBe("deny");
  });
});

describe("pipeRule", () => {
  test("returns correct shape", () => {
    const r = pipeRule(["curl"], ["bash"], "test reason");
    expect(r.kind).toBe("pipe");
    expect(r.from).toEqual(["curl"]);
    expect(r.into).toEqual(["bash"]);
    expect(r.decision).toBe("ask");
  });
});

describe("redirectRule", () => {
  test("returns correct shape", () => {
    const r = redirectRule("redirect to config");
    expect(r.kind).toBe("redirect");
    expect(r.decision).toBe("ask");
  });
});

describe("recurseRule", () => {
  test("returns kind recurse", () => {
    const r = recurseRule();
    expect(r.kind).toBe("recurse");
  });
});

describe("protectWrite", () => {
  test("returns path rule for write", () => {
    const r = protectWrite(/\.env$/, "test");
    expect(r.kind).toBe("path");
    expect(r.event).toBe("write");
    expect(r.decision).toBe("ask");
  });
});

describe("protectRead", () => {
  test("returns path rule for read", () => {
    const r = protectRead(/\.ssh\//, "test");
    expect(r.kind).toBe("path");
    expect(r.event).toBe("read");
    expect(r.decision).toBe("ask");
  });
});
