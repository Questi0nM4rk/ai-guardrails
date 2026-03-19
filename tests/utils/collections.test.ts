import { describe, expect, test } from "bun:test";
import { groupBy } from "@/utils/collections";

describe("groupBy", () => {
  test("groups items by string key", () => {
    const items = [
      { file: "a.ts", val: 1 },
      { file: "b.ts", val: 2 },
      { file: "a.ts", val: 3 },
    ] as const;
    const result = groupBy(items, (i) => i.file);
    expect(result.size).toBe(2);
    expect(result.get("a.ts")).toHaveLength(2);
    expect(result.get("b.ts")).toHaveLength(1);
  });

  test("returns empty map for empty input", () => {
    const result = groupBy([], (i: { k: string }) => i.k);
    expect(result.size).toBe(0);
  });

  test("groups all items under same key when all keys are equal", () => {
    const items = [{ k: "x" }, { k: "x" }, { k: "x" }];
    const result = groupBy(items, (i) => i.k);
    expect(result.size).toBe(1);
    expect(result.get("x")).toHaveLength(3);
  });

  test("preserves insertion order within groups", () => {
    const items = [
      { k: "a", n: 1 },
      { k: "b", n: 2 },
      { k: "a", n: 3 },
    ];
    const group = groupBy(items, (i) => i.k).get("a");
    expect(group?.map((i) => i.n)).toEqual([1, 3]);
  });
});
