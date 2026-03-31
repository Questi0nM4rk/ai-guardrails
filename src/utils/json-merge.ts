export type JsonObject = Record<string, unknown>;

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
 * Returns an empty object if the file does not exist, is not valid JSON, or is not an object.
 */
export async function readJsonObject(
  path: string,
  fileManager: {
    exists(path: string): Promise<boolean>;
    readText(path: string): Promise<string>;
  }
): Promise<JsonObject> {
  const exists = await fileManager.exists(path);
  if (!exists) return {};
  const text = await fileManager.readText(path);
  try {
    const parsed: unknown = JSON.parse(text);
    if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as JsonObject;
    }
    return {};
  } catch {
    return {};
  }
}
