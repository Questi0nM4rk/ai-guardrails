import { describe, expect, test } from "bun:test";
import { expandFlags, hasFlag } from "@/check/flag-aliases";

describe("expandFlags", () => {
  test("passes through flags with no aliases", () => {
    const result = expandFlags(["--some-unknown"]);
    expect(result).toEqual(["--some-unknown"]);
  });

  test("expands -r to include --recursive", () => {
    const result = expandFlags(["-r"]);
    expect(result).toContain("-r");
    expect(result).toContain("--recursive");
  });

  test("expands --recursive to include -r and -R", () => {
    const result = expandFlags(["--recursive"]);
    expect(result).toContain("--recursive");
    expect(result).toContain("-r");
    expect(result).toContain("-R");
  });

  test("expands -f to include --force", () => {
    const result = expandFlags(["-f"]);
    expect(result).toContain("-f");
    expect(result).toContain("--force");
  });

  test("expands --force to include -f", () => {
    const result = expandFlags(["--force"]);
    expect(result).toContain("--force");
    expect(result).toContain("-f");
  });

  test("expands -D to --delete and --force (plus their aliases)", () => {
    const result = expandFlags(["-D"]);
    expect(result).toContain("-D");
    expect(result).toContain("--delete");
    expect(result).toContain("--force");
    expect(result).toContain("-d");
    expect(result).toContain("-f");
  });

  test("expands --no-verify to include -n", () => {
    const result = expandFlags(["--no-verify"]);
    expect(result).toContain("--no-verify");
    expect(result).toContain("-n");
  });

  test("expands -n to include --no-verify", () => {
    const result = expandFlags(["-n"]);
    expect(result).toContain("-n");
    expect(result).toContain("--no-verify");
  });

  test("handles multiple flags", () => {
    const result = expandFlags(["-r", "--force"]);
    expect(result).toContain("-r");
    expect(result).toContain("--recursive");
    expect(result).toContain("--force");
    expect(result).toContain("-f");
  });

  test("does not produce duplicates", () => {
    const result = expandFlags(["-f", "--force"]);
    const unique = new Set(result);
    expect(result).toHaveLength(unique.size);
  });
});

describe("hasFlag", () => {
  test("exact match returns true", () => {
    expect(hasFlag(["--force"], "--force")).toBe(true);
  });

  test("different flag returns false", () => {
    expect(hasFlag(["--force"], "--recursive")).toBe(false);
  });

  test("parameterized form matches via startsWith", () => {
    expect(hasFlag(["--force-with-lease=origin/main:main"], "--force-with-lease")).toBe(
      true
    );
  });

  test("empty expanded list returns false", () => {
    expect(hasFlag([], "--force")).toBe(false);
  });

  test("does not false-positive on prefix substring", () => {
    // --force should NOT match --force-with-lease (no = separator)
    expect(hasFlag(["--force-with-lease"], "--force")).toBe(false);
  });
});
