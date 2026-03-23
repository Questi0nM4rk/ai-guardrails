import { describe, expect, test } from "bun:test";
import type { Interface as ReadlineInterface } from "node:readline";
import type { ReadlineHandle } from "@/init/prompt";
import {
  askChoice,
  askCommaSeparated,
  askFileConflict,
  askText,
  askYesNo,
} from "@/init/prompt";

/**
 * Creates a `() => ReadlineInterface` factory from a sequence of answers.
 * The returned readline only implements question() and close() — the two
 * methods our prompt helpers actually use. Cast is at the factory boundary
 * and is safe because ReadlineInterface satisfies ReadlineHandle structurally.
 */
function fakeReadline(answers: string[]): () => ReadlineInterface {
  let idx = 0;
  return () => {
    const handle: ReadlineHandle = {
      question(_prompt: string, cb: (answer: string) => void): void {
        cb(answers[idx++] ?? "");
      },
      close(): void {},
    };
    // Single cast at factory boundary — safe: ReadlineInterface satisfies ReadlineHandle.
    return handle as unknown as ReadlineInterface;
  };
}

describe("askYesNo", () => {
  test("returns true for 'y' input", async () => {
    const result = await askYesNo(fakeReadline(["y"]), "Continue?", false);
    expect(result).toBe(true);
  });

  test("returns true for 'yes' input", async () => {
    const result = await askYesNo(fakeReadline(["yes"]), "Continue?", false);
    expect(result).toBe(true);
  });

  test("returns false for 'n' input", async () => {
    const result = await askYesNo(fakeReadline(["n"]), "Continue?", true);
    expect(result).toBe(false);
  });

  test("returns false for 'no' input", async () => {
    const result = await askYesNo(fakeReadline(["no"]), "Continue?", true);
    expect(result).toBe(false);
  });

  test("returns defaultYes=true on empty input", async () => {
    const result = await askYesNo(fakeReadline([""]), "Continue?", true);
    expect(result).toBe(true);
  });

  test("returns defaultYes=false on empty input", async () => {
    const result = await askYesNo(fakeReadline([""]), "Continue?", false);
    expect(result).toBe(false);
  });
});

describe("askChoice", () => {
  const choices = ["strict", "standard", "minimal"] as const;

  test("returns valid choice", async () => {
    const result = await askChoice(
      fakeReadline(["strict"]),
      "Profile?",
      choices,
      "standard"
    );
    expect(result).toBe("strict");
  });

  test("returns default on empty input", async () => {
    const result = await askChoice(fakeReadline([""]), "Profile?", choices, "standard");
    expect(result).toBe("standard");
  });

  test("retries on invalid input then accepts valid", async () => {
    const result = await askChoice(
      fakeReadline(["bad", "minimal"]),
      "Profile?",
      choices,
      "standard"
    );
    expect(result).toBe("minimal");
  });
});

describe("askText", () => {
  test("returns trimmed input", async () => {
    const result = await askText(fakeReadline(["  hello  "]), "Name?", "default");
    expect(result).toBe("hello");
  });

  test("returns defaultValue on empty input", async () => {
    const result = await askText(fakeReadline([""]), "Name?", "default");
    expect(result).toBe("default");
  });

  test("returns empty string default when given", async () => {
    const result = await askText(fakeReadline([""]), "Name?", "");
    expect(result).toBe("");
  });
});

describe("askCommaSeparated", () => {
  test("returns empty array on empty input", async () => {
    const result = await askCommaSeparated(fakeReadline([""]), "Rules?");
    expect(result).toEqual([]);
  });

  test("splits on comma and trims whitespace", async () => {
    const result = await askCommaSeparated(fakeReadline([" a , b , c "]), "Rules?");
    expect(result).toEqual(["a", "b", "c"]);
  });

  test("filters out empty segments", async () => {
    const result = await askCommaSeparated(fakeReadline(["a,,b,"]), "Rules?");
    expect(result).toEqual(["a", "b"]);
  });
});

describe("askFileConflict", () => {
  test("returns skip on empty input", async () => {
    const result = await askFileConflict(fakeReadline([""]), "biome.jsonc");
    expect(result).toBe("skip");
  });

  test("returns merge on 'merge' input", async () => {
    const result = await askFileConflict(fakeReadline(["merge"]), "biome.jsonc");
    expect(result).toBe("merge");
  });

  test("returns replace on 'replace' input", async () => {
    const result = await askFileConflict(fakeReadline(["replace"]), "biome.jsonc");
    expect(result).toBe("replace");
  });

  test("returns skip on 'skip' input", async () => {
    const result = await askFileConflict(fakeReadline(["skip"]), "biome.jsonc");
    expect(result).toBe("skip");
  });

  test("retries on invalid input then accepts valid", async () => {
    const result = await askFileConflict(fakeReadline(["wat", "merge"]), "biome.jsonc");
    expect(result).toBe("merge");
  });
});
