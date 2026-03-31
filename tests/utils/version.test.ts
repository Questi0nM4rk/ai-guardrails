import { describe, expect, test } from "bun:test";
import { getVersion, semverLt } from "@/utils/version";

describe("semverLt", () => {
  test("returns false when versions are equal", () => {
    expect(semverLt("3.1.0", "3.1.0")).toBe(false);
  });

  test("returns true when major version is lower", () => {
    expect(semverLt("2.0.0", "3.0.0")).toBe(true);
  });

  test("returns false when major version is higher", () => {
    expect(semverLt("4.0.0", "3.0.0")).toBe(false);
  });

  test("returns true when minor version is lower", () => {
    expect(semverLt("3.0.0", "3.1.0")).toBe(true);
  });

  test("returns false when minor version is higher", () => {
    expect(semverLt("3.2.0", "3.1.0")).toBe(false);
  });

  test("returns true when patch version is lower", () => {
    expect(semverLt("3.1.0", "3.1.1")).toBe(true);
  });

  test("returns false when patch version is higher", () => {
    expect(semverLt("3.1.2", "3.1.1")).toBe(false);
  });

  test("missing parts default to 0", () => {
    // "3.1" is treated as "3.1.0"
    expect(semverLt("3.1", "3.1.0")).toBe(false);
    expect(semverLt("3.1", "3.1.1")).toBe(true);
  });

  test("returns false for 0.0.0 compared to 0.0.0", () => {
    expect(semverLt("0.0.0", "0.0.0")).toBe(false);
  });
});

describe("getVersion", () => {
  test("returns a string matching X.Y.Z", () => {
    const version = getVersion();
    expect(typeof version).toBe("string");
    expect(/^\d+\.\d+\.\d+$/.test(version)).toBe(true);
  });
});
