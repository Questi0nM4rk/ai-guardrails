import { describe, expect, test } from "bun:test";
import { expandFlags, hasFlag } from "@/check/flag-aliases";

describe("hasFlag", () => {
  test("returns true for exact match", () => {
    expect(hasFlag(["-r", "-f"], "-r")).toBe(true);
  });

  test("returns true when short flag matches wanted long flag via alias", () => {
    expect(hasFlag(["-r", "-f"], "--recursive")).toBe(true);
  });

  test("returns true when long flag matches wanted short flag via alias", () => {
    expect(hasFlag(["--force"], "-f")).toBe(true);
  });

  test("returns false when flag is not present and has no alias match", () => {
    expect(hasFlag(["--verbose"], "-v")).toBe(false);
  });

  test("returns true for parameterized flag via startsWith", () => {
    expect(hasFlag(["--force-with-lease=origin/main"], "--force-with-lease")).toBe(
      true
    );
  });

  test("returns false when parameterized flag does not match different flag", () => {
    expect(hasFlag(["--force-with-lease"], "--force")).toBe(false);
  });

  test("returns true for -R alias of --recursive", () => {
    expect(hasFlag(["-R"], "--recursive")).toBe(true);
  });

  test("returns true for --recursive alias of -R", () => {
    expect(hasFlag(["--recursive"], "-R")).toBe(true);
  });

  test("returns true for --force alias of -f", () => {
    expect(hasFlag(["--force"], "-f")).toBe(true);
  });

  test("returns true for -f alias of --force", () => {
    expect(hasFlag(["-f"], "--force")).toBe(true);
  });

  test("returns true for -d alias of --delete", () => {
    expect(hasFlag(["-d"], "--delete")).toBe(true);
  });

  test("returns true for --delete alias of -d", () => {
    expect(hasFlag(["--delete"], "-d")).toBe(true);
  });

  test("returns true for -n alias of --no-verify", () => {
    expect(hasFlag(["-n"], "--no-verify")).toBe(true);
  });

  test("returns true for --no-verify alias of -n", () => {
    expect(hasFlag(["--no-verify"], "-n")).toBe(true);
  });

  test("returns false for empty flags array", () => {
    expect(hasFlag([], "--force")).toBe(false);
  });

  test("returns false for unknown flag with no aliases", () => {
    expect(hasFlag(["--unknown"], "--force")).toBe(false);
  });

  test("handles parameterized alias form with equals", () => {
    expect(hasFlag(["--delete=branch"], "--delete")).toBe(true);
  });

  test("does not match partial flag names without alias", () => {
    expect(hasFlag(["--forces"], "--force")).toBe(false);
  });
});

describe("expandFlags", () => {
  test("expands -D to --delete and --force", () => {
    const result = expandFlags(["-D"]);
    expect(result).toContain("--delete");
    expect(result).toContain("--force");
    expect(result).toHaveLength(2);
  });

  test("passes through non-expansion flags unchanged", () => {
    const result = expandFlags(["-r", "-f"]);
    expect(result).toEqual(["-r", "-f"]);
  });

  test("expands -D among other flags", () => {
    const result = expandFlags(["-D", "-v"]);
    expect(result).toContain("--delete");
    expect(result).toContain("--force");
    expect(result).toContain("-v");
    expect(result).toHaveLength(3);
  });

  test("returns empty array for empty input", () => {
    expect(expandFlags([])).toEqual([]);
  });

  test("deduplicates when expansion overlaps with existing flag", () => {
    const result = expandFlags(["--force", "-D"]);
    expect(result).toContain("--force");
    expect(result).toContain("--delete");
    expect(result).toHaveLength(2); // --force appears once despite overlap
  });
});

describe("hasFlag + expandFlags integration", () => {
  test("git branch -D matches --delete via expansion + alias", () => {
    const expanded = expandFlags(["-D"]);
    expect(hasFlag(expanded, "--delete")).toBe(true);
    expect(hasFlag(expanded, "--force")).toBe(true);
  });

  test("git branch -D matches -d via expansion + alias", () => {
    const expanded = expandFlags(["-D"]);
    expect(hasFlag(expanded, "-d")).toBe(true);
    expect(hasFlag(expanded, "-f")).toBe(true);
  });
});
