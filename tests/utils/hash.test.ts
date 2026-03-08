import { describe, expect, test } from "bun:test";
import { HASH_PREFIX, makeHashHeader, withHashHeader } from "@/utils/hash";

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

describe("withHashHeader", () => {
    test("prepends the hash header line followed by a newline", () => {
        const body = "line1\nline2\nline3\n";
        const result = withHashHeader(body);
        const [headerLine, ...rest] = result.split("\n");
        expect(headerLine).toBe(makeHashHeader(body));
        expect(rest.join("\n")).toBe(body);
    });

    test("header in output matches the body content hash", () => {
        const body = "original content\n";
        const result = withHashHeader(body);
        const expectedHeader = makeHashHeader(body);
        expect(result.startsWith(expectedHeader)).toBe(true);
    });

    test("works with empty body", () => {
        const result = withHashHeader("");
        const expectedHeader = makeHashHeader("");
        expect(result).toBe(`${expectedHeader}\n`);
    });

    test("handles multi-line file content correctly", () => {
        const body = `${Array.from({ length: 50 }, (_, i) => `line ${i + 1}`).join("\n")}\n`;
        const result = withHashHeader(body);
        const expectedHeader = makeHashHeader(body);
        expect(result).toBe(`${expectedHeader}\n${body}`);
    });
});
