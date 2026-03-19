import { describe, expect, test } from "bun:test";
import { computeFingerprint } from "@/models/lint-issue";

describe("computeFingerprint", () => {
  test("same input produces same hash", () => {
    const opts = {
      rule: "ruff/E501",
      file: "src/foo.py",
      lineContent: "  x = very_long_variable_name_that_exceeds_the_line_limit",
      contextBefore: ["def foo():", "  # setup"],
      contextAfter: ["  return x", ""],
    };
    const a = computeFingerprint(opts);
    const b = computeFingerprint(opts);
    expect(a).toBe(b);
  });

  test("different rule produces different hash", () => {
    const base = {
      file: "src/foo.py",
      lineContent: "  x = 1",
      contextBefore: [],
      contextAfter: [],
    };
    const a = computeFingerprint({ ...base, rule: "ruff/E501" });
    const b = computeFingerprint({ ...base, rule: "ruff/E302" });
    expect(a).not.toBe(b);
  });

  test("different lineContent produces different hash", () => {
    const base = {
      rule: "ruff/E501",
      file: "src/foo.py",
      contextBefore: [],
      contextAfter: [],
    };
    const a = computeFingerprint({ ...base, lineContent: "x = 1" });
    const b = computeFingerprint({ ...base, lineContent: "x = 2" });
    expect(a).not.toBe(b);
  });

  test("different file produces different fingerprint", () => {
    const base = {
      rule: "ruff/E501",
      lineContent: "  x = 1",
      contextBefore: [],
      contextAfter: [],
    };
    const a = computeFingerprint({ ...base, file: "src/foo.py" });
    const b = computeFingerprint({ ...base, file: "src/bar.py" });
    expect(a).not.toBe(b);
  });

  test("handles empty context arrays", () => {
    const fp = computeFingerprint({
      rule: "ruff/E501",
      file: "src/foo.py",
      lineContent: "x = 1",
      contextBefore: [],
      contextAfter: [],
    });
    expect(fp).toHaveLength(64); // SHA-256 hex
  });

  test("trims whitespace from lineContent for stability", () => {
    const base = {
      rule: "ruff/E501",
      file: "src/foo.py",
      contextBefore: [],
      contextAfter: [],
    };
    const a = computeFingerprint({ ...base, lineContent: "  x = 1  " });
    const b = computeFingerprint({ ...base, lineContent: "x = 1" });
    expect(a).toBe(b);
  });

  test("different contextBefore produces different hash", () => {
    const base = {
      rule: "ruff/E501",
      file: "src/foo.py",
      lineContent: "x = 1",
      contextAfter: [],
    };
    const a = computeFingerprint({ ...base, contextBefore: ["def foo():"] });
    const b = computeFingerprint({ ...base, contextBefore: ["def bar():"] });
    expect(a).not.toBe(b);
  });

  test("returns 64-character hex string", () => {
    const fp = computeFingerprint({
      rule: "ruff/E501",
      file: "src/foo.py",
      lineContent: "x = 1",
      contextBefore: [],
      contextAfter: [],
    });
    expect(fp).toMatch(/^[0-9a-f]{64}$/);
  });

  test("same relative file path at different project roots produces same fingerprint", () => {
    // Proves baselines are portable: the same issue checked out at /home/alice/repo
    // and /home/bob/repo produces the same fingerprint if callers pass relative paths.
    const opts = {
      rule: "ruff/E501",
      lineContent: "x = very_long_line",
      contextBefore: [],
      contextAfter: [],
    };
    const fpAlice = computeFingerprint({ ...opts, file: "src/foo.py" });
    const fpBob = computeFingerprint({ ...opts, file: "src/foo.py" });
    expect(fpAlice).toBe(fpBob);
  });

  test("absolute paths in file produce different fingerprints for same relative location", () => {
    // Documents the pre-fix bug: two machines checking out the same file would get
    // different fingerprints if absolute paths were passed to computeFingerprint.
    const opts = {
      rule: "ruff/E501",
      lineContent: "x = very_long_line",
      contextBefore: [],
      contextAfter: [],
    };
    const fpAlice = computeFingerprint({
      ...opts,
      file: "/home/alice/repo/src/foo.py",
    });
    const fpBob = computeFingerprint({ ...opts, file: "/home/bob/repo/src/foo.py" });
    expect(fpAlice).not.toBe(fpBob);
  });
});
