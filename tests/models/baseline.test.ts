import { describe, expect, test } from "bun:test";
import { type BaselineEntry, classifyFingerprint, loadBaseline } from "@/models/baseline";

function makeEntry(fingerprint: string): BaselineEntry {
  return {
    fingerprint,
    rule: "ruff/E501",
    linter: "ruff",
    file: "src/foo.py",
    line: 10,
    message: "Line too long",
    capturedAt: "2026-03-08T00:00:00.000Z",
  };
}

describe("loadBaseline", () => {
  test("builds map keyed by fingerprint", () => {
    const entries = [makeEntry("abc123"), makeEntry("def456")];
    const map = loadBaseline(entries);
    expect(map.size).toBe(2);
    expect(map.get("abc123")?.rule).toBe("ruff/E501");
    expect(map.get("def456")?.linter).toBe("ruff");
  });

  test("returns empty map for empty array", () => {
    const map = loadBaseline([]);
    expect(map.size).toBe(0);
  });

  test("last entry wins for duplicate fingerprints", () => {
    const a = { ...makeEntry("fp1"), line: 5 };
    const b = { ...makeEntry("fp1"), line: 10 };
    const map = loadBaseline([a, b]);
    expect(map.size).toBe(1);
    expect(map.get("fp1")?.line).toBe(10);
  });
});

describe("classifyFingerprint", () => {
  test("returns 'existing' when fingerprint is in baseline", () => {
    const map = loadBaseline([makeEntry("known-fp")]);
    expect(classifyFingerprint("known-fp", map)).toBe("existing");
  });

  test("returns 'new' when fingerprint is not in baseline", () => {
    const map = loadBaseline([makeEntry("known-fp")]);
    expect(classifyFingerprint("unknown-fp", map)).toBe("new");
  });

  test("returns 'new' for empty baseline", () => {
    const map = loadBaseline([]);
    expect(classifyFingerprint("any-fp", map)).toBe("new");
  });
});
