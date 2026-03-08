import { describe, expect, test } from "bun:test";
import { HASH_PREFIX, makeHashHeader, verifyHash } from "@/utils/hash";

describe("HASH_PREFIX", () => {
  test("has correct value", () => {
    expect(HASH_PREFIX).toBe("# ai-guardrails:sha256=");
  });
});

describe("makeHashHeader", () => {
  test("returns a line starting with the hash prefix", () => {
    const header = makeHashHeader("some content");
    expect(header).toStartWith(HASH_PREFIX);
  });

  test("returns a 64-char hex hash after the prefix", () => {
    const header = makeHashHeader("some content");
    const hash = header.slice(HASH_PREFIX.length);
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
  });

  test("same content produces same header", () => {
    const a = makeHashHeader("content");
    const b = makeHashHeader("content");
    expect(a).toBe(b);
  });

  test("different content produces different header", () => {
    const a = makeHashHeader("content a");
    const b = makeHashHeader("content b");
    expect(a).not.toBe(b);
  });
});

describe("verifyHash", () => {
  test("roundtrip: makeHashHeader + verifyHash returns true", () => {
    const body = "line1\nline2\nline3\n";
    const header = makeHashHeader(body);
    const fullFile = `${header}\n${body}`;
    expect(verifyHash(fullFile)).toBe(true);
  });

  test("returns false for tampered content", () => {
    const body = "original content\n";
    const header = makeHashHeader(body);
    const tampered = `${header}\ntampered content\n`;
    expect(verifyHash(tampered)).toBe(false);
  });

  test("returns false for file with no hash header", () => {
    const content = "no header here\n";
    expect(verifyHash(content)).toBe(false);
  });

  test("returns false for file with empty content after header", () => {
    const header = makeHashHeader("");
    const fileWithJustHeader = `${header}\n`;
    // body is "" so hash of "" should match
    expect(verifyHash(fileWithJustHeader)).toBe(true);
  });

  test("handles multi-line file content correctly", () => {
    const body = `${Array.from({ length: 50 }, (_, i) => `line ${i + 1}`).join("\n")}\n`;
    const header = makeHashHeader(body);
    const fullFile = `${header}\n${body}`;
    expect(verifyHash(fullFile)).toBe(true);
  });
});
