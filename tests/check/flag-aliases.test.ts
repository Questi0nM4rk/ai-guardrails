import { describe, expect, test } from "bun:test";
import { normaliseFlags } from "@/check/flag-aliases";

describe("normaliseFlags", () => {
  test("expands rm short flags to long forms", () => {
    expect(normaliseFlags("rm", ["-r", "-f"])).toEqual(["--recursive", "--force"]);
  });

  test("passes through unknown flags unchanged", () => {
    expect(normaliseFlags("rm", ["-v", "--verbose"])).toEqual(["-v", "--verbose"]);
  });

  test("passes through all flags for unknown commands", () => {
    expect(normaliseFlags("ls", ["-l", "-a"])).toEqual(["-l", "-a"]);
  });

  test("expands git -f to --force", () => {
    expect(normaliseFlags("git", ["-f"])).toEqual(["--force"]);
  });

  test("expands git -n to --no-verify", () => {
    expect(normaliseFlags("git", ["-n"])).toEqual(["--no-verify"]);
  });

  test("expands git -D to --delete --force (multi-flag)", () => {
    expect(normaliseFlags("git", ["-D"])).toEqual(["--delete", "--force"]);
  });

  test("expands chmod -R to --recursive", () => {
    expect(normaliseFlags("chmod", ["-R"])).toEqual(["--recursive"]);
  });

  test("mixes expanded and passthrough flags", () => {
    expect(normaliseFlags("rm", ["-r", "--verbose", "-f"])).toEqual([
      "--recursive",
      "--verbose",
      "--force",
    ]);
  });
});
