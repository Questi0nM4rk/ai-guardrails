import { describe, expect, test } from "bun:test";
import { expandFlags, hasFlag } from "@/check/flag-aliases";

describe("expandFlags", () => {
  test("expands -D to --delete and --force", () => {
    const result = expandFlags(["-D"]);
    expect(result).toContain("--delete");
    expect(result).toContain("--force");
  });

  test("passes through flags without expansions", () => {
    const result = expandFlags(["--verbose"]);
    expect(result).toContain("--verbose");
  });

  test("adds alias equivalents transitively", () => {
    const result = expandFlags(["-r"]);
    expect(result).toContain("-r");
    expect(result).toContain("--recursive");
    expect(result).toContain("-R");
  });

  test("-R resolves transitively to -r and --recursive", () => {
    const result = expandFlags(["-R"]);
    expect(result).toContain("-R");
    expect(result).toContain("--recursive");
    expect(result).toContain("-r");
  });

  test("deduplicates when expansion overlaps", () => {
    const result = expandFlags(["--force", "-D"]);
    expect(result).toContain("--force");
    expect(result).toContain("--delete");
    expect(result.filter((f) => f === "--force")).toHaveLength(1);
  });

  test("returns empty array for empty input", () => {
    expect(expandFlags([])).toEqual([]);
  });

  test("mixes expanded and passthrough flags", () => {
    const result = expandFlags(["-r", "--verbose", "-f"]);
    expect(result).toContain("-r");
    expect(result).toContain("--recursive");
    expect(result).toContain("-R");
    expect(result).toContain("--verbose");
    expect(result).toContain("-f");
    expect(result).toContain("--force");
  });
});

describe("hasFlag", () => {
  test("matches exact flag", () => {
    expect(hasFlag(["--force"], "--force")).toBe(true);
  });

  test("does not match absent flag", () => {
    expect(hasFlag(["--verbose"], "--force")).toBe(false);
  });

  test("handles parameterized flag (--force-with-lease=refspec)", () => {
    expect(hasFlag(["--force-with-lease=origin/main"], "--force-with-lease")).toBe(
      true
    );
  });

  test("does not match --force-with-lease as --force", () => {
    expect(hasFlag(["--force-with-lease"], "--force")).toBe(false);
  });
});

describe("hasFlag + expandFlags integration", () => {
  test("-r matches --recursive via alias expansion", () => {
    const expanded = expandFlags(["-r"]);
    expect(hasFlag(expanded, "--recursive")).toBe(true);
  });

  test("--force matches -f via alias expansion", () => {
    const expanded = expandFlags(["--force"]);
    expect(hasFlag(expanded, "-f")).toBe(true);
  });

  test("-R matches --recursive via transitive alias", () => {
    const expanded = expandFlags(["-R"]);
    expect(hasFlag(expanded, "--recursive")).toBe(true);
    expect(hasFlag(expanded, "-r")).toBe(true);
  });

  test("git branch -D matches --delete and --force", () => {
    const expanded = expandFlags(["-D"]);
    expect(hasFlag(expanded, "--delete")).toBe(true);
    expect(hasFlag(expanded, "--force")).toBe(true);
  });

  test("-n matches --no-verify via alias", () => {
    const expanded = expandFlags(["-n"]);
    expect(hasFlag(expanded, "--no-verify")).toBe(true);
  });
});
