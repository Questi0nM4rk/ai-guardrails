import { describe, expect, test } from "bun:test";
import { deepMerge } from "@/utils/deep-merge";

describe("deepMerge", () => {
  test("simple flat merge combines keys from both objects", () => {
    const result = deepMerge({ a: 1, b: 2 }, { c: 3 });
    expect(result).toEqual({ a: 1, b: 2, c: 3 });
  });

  test("override wins on key collision", () => {
    const result = deepMerge({ a: 1, b: 2 }, { b: 3, c: 4 });
    expect(result).toEqual({ a: 1, b: 3, c: 4 });
  });

  test("base extra keys are preserved when not in override", () => {
    const result = deepMerge({ a: 1, b: 2, extra: "keep" }, { b: 99 });
    expect(result).toEqual({ a: 1, b: 99, extra: "keep" });
  });

  test("nested objects are merged recursively", () => {
    const result = deepMerge({ nested: { x: 1 } }, { nested: { y: 2 } });
    expect(result).toEqual({ nested: { x: 1, y: 2 } });
  });

  test("deeply nested merge preserves base keys at each level", () => {
    const result = deepMerge(
      { a: { b: { c: 1, d: 2 } } },
      { a: { b: { d: 99, e: 3 } } }
    );
    expect(result).toEqual({ a: { b: { c: 1, d: 99, e: 3 } } });
  });

  test("arrays are not merged — override wins entirely", () => {
    const result = deepMerge({ arr: [1] }, { arr: [2, 3] });
    expect(result).toEqual({ arr: [2, 3] });
  });

  test("array in base is replaced by array in override", () => {
    const result = deepMerge({ arr: [1, 2, 3] }, { arr: [] });
    expect(result).toEqual({ arr: [] });
  });

  test("type override: primitive in base replaced by object in override", () => {
    const result = deepMerge({ a: 1 }, { a: { nested: true } });
    expect(result).toEqual({ a: { nested: true } });
  });

  test("type override: object in base replaced by primitive in override", () => {
    const result = deepMerge({ a: { nested: true } }, { a: 42 });
    expect(result).toEqual({ a: 42 });
  });

  test("empty base returns clone of override", () => {
    const result = deepMerge({}, { a: 1, b: 2 });
    expect(result).toEqual({ a: 1, b: 2 });
  });

  test("empty override returns clone of base", () => {
    const result = deepMerge({ a: 1, b: 2 }, {});
    expect(result).toEqual({ a: 1, b: 2 });
  });

  test("both empty returns empty object", () => {
    const result = deepMerge({}, {});
    expect(result).toEqual({});
  });

  test("does not mutate the base object", () => {
    const base = { a: 1, nested: { x: 1 } };
    deepMerge(base, { a: 2, nested: { y: 2 } });
    expect(base).toEqual({ a: 1, nested: { x: 1 } });
  });

  test("does not mutate the override object", () => {
    const override = { b: 2, nested: { y: 2 } };
    deepMerge({ a: 1, nested: { x: 1 } }, override);
    expect(override).toEqual({ b: 2, nested: { y: 2 } });
  });

  test("null value in override replaces base value", () => {
    const result = deepMerge({ a: 1 }, { a: null });
    expect(result).toEqual({ a: null });
  });

  test("null value in base is replaced by object in override", () => {
    const result = deepMerge({ a: null }, { a: { x: 1 } });
    expect(result).toEqual({ a: { x: 1 } });
  });

  test("string values are overridden correctly", () => {
    const result = deepMerge({ name: "base" }, { name: "override" });
    expect(result).toEqual({ name: "override" });
  });

  test("mixed nested: only overlapping keys are merged, rest preserved", () => {
    const result = deepMerge(
      { a: { x: 1, y: 2 }, b: "unchanged" },
      { a: { y: 99, z: 3 } }
    );
    expect(result).toEqual({ a: { x: 1, y: 99, z: 3 }, b: "unchanged" });
  });
});
