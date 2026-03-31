import { z } from "zod";

export type JsonObject = Record<string, unknown>;

const JsonObjectSchema = z.record(z.unknown());

/**
 * Returns true when `v` is a plain (non-null, non-array) object.
 * Use this instead of `as JsonObject` casts at runtime boundaries.
 */
export function isJsonObject(v: unknown): v is JsonObject {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/**
 * Shallow merge two JSON objects without overwriting keys already present in base.
 * Only top-level keys from `additions` that are absent in `base` are copied.
 */
export function mergeWithoutOverwrite(
  base: JsonObject,
  additions: JsonObject
): JsonObject {
  const result: JsonObject = { ...base };
  for (const [key, value] of Object.entries(additions)) {
    if (!(key in result)) {
      result[key] = value;
    }
  }
  return result;
}

/**
 * Read a file and parse it as a JSON object.
 * Returns undefined if the file has invalid JSON or is not an object (caller decides how to handle).
 * Returns an empty object if the file does not exist.
 */
export async function readJsonObject(
  path: string,
  fileManager: {
    exists(path: string): Promise<boolean>;
    readText(path: string): Promise<string>;
  }
): Promise<JsonObject | undefined> {
  const exists = await fileManager.exists(path);
  if (!exists) return {};
  const text = await fileManager.readText(path);
  try {
    const parsed: unknown = JSON.parse(text);
    const result = JsonObjectSchema.safeParse(parsed);
    if (!result.success) return undefined;
    return result.data;
  } catch {
    return undefined;
  }
}
