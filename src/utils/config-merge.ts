import { extname, join } from "node:path";
import { parse as parseToml, stringify as stringifyToml } from "smol-toml";
import type { ConfigStrategy } from "@/config/schema";
import type { FileManager } from "@/infra/file-manager";
import { deepMerge } from "@/utils/deep-merge";
import { withHashHeader, withJsoncHashHeader } from "@/utils/hash";

/** File extensions that support structured merge (JSON/JSONC and TOML). */
const MERGEABLE_EXTENSIONS = new Set([".json", ".jsonc", ".toml"]);

function isMergeable(configFile: string): boolean {
  return MERGEABLE_EXTENSIONS.has(extname(configFile));
}

/**
 * Strip single-line and block comments from JSONC, respecting string literals
 * so URLs and embedded slashes are preserved.
 */
function stripJsoncComments(text: string): string {
  let result = "";
  let inString = false;
  let isEscaped = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i] ?? "";
    if (isEscaped) {
      result += ch;
      isEscaped = false;
      continue;
    }
    if (ch === "\\" && inString) {
      result += ch;
      isEscaped = true;
      continue;
    }
    if (ch === '"') {
      inString = !inString;
      result += ch;
      continue;
    }
    if (!inString && ch === "/" && text[i + 1] === "/") {
      while (i < text.length && text[i] !== "\n") i++;
      if (i < text.length) result += "\n";
      continue;
    }
    if (!inString && ch === "/" && text[i + 1] === "*") {
      i += 2;
      while (i < text.length && !(text[i] === "*" && text[i + 1] === "/")) i++;
      i++;
      continue;
    }
    result += ch;
  }
  return result;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseForMerge(
  content: string,
  configFile: string
): Record<string, unknown> | null {
  try {
    const ext = extname(configFile);
    if (ext === ".toml") {
      const parsed: unknown = parseToml(content);
      return isPlainObject(parsed) ? parsed : null;
    }
    if (ext === ".json" || ext === ".jsonc") {
      const stripped = stripJsoncComments(content);
      const parsed: unknown = JSON.parse(stripped);
      return isPlainObject(parsed) ? parsed : null;
    }
    return null;
  } catch {
    // Malformed TOML/JSON — cannot merge, caller should skip
    return null;
  }
}

function serializeForMerge(data: Record<string, unknown>, configFile: string): string {
  const ext = extname(configFile);
  if (ext === ".toml") {
    return stringifyToml(data);
  }
  return JSON.stringify(data, null, 2);
}

/**
 * Apply config merge strategy: merge/replace/skip for an existing file.
 * Returns the content to write, or null if the file should be skipped.
 */
export async function applyStrategy(
  projectDir: string,
  configFile: string,
  generated: string,
  strategy: ConfigStrategy,
  fileManager: FileManager
): Promise<string | null> {
  const dest = join(projectDir, configFile);
  const exists = await fileManager.exists(dest);

  if (!exists) return generated;
  if (strategy === "skip") return null;
  if (strategy === "replace") return generated;

  // strategy === "merge"
  if (!isMergeable(configFile)) return generated;

  const existingText = await fileManager.readText(dest);
  const existingData = parseForMerge(existingText, configFile);
  const generatedData = parseForMerge(generated, configFile);

  // If either side fails to parse, skip the file rather than silently
  // replacing the user's content with generated output.
  if (existingData === null || generatedData === null) return null;

  // User settings win on key collision: generated is the base, existing overlays on top.
  // This preserves user customisations (e.g. line-length = 120) while adding any
  // guardrails keys that are absent from the existing file.
  const merged = deepMerge(generatedData, existingData);
  const serialized = serializeForMerge(merged, configFile);
  const ext = extname(configFile);
  if (ext === ".jsonc") return withJsoncHashHeader(serialized);
  if (ext === ".toml") return withHashHeader(serialized);
  return serialized;
}
