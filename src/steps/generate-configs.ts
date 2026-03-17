import { dirname, extname, join } from "node:path";
import { parse as parseToml, stringify as stringifyToml } from "smol-toml";
import type { ConfigStrategy, ResolvedConfig } from "@/config/schema";
import { generateLefthookConfig, lefthookGenerator } from "@/generators/lefthook";
import { ALL_GENERATORS } from "@/generators/registry";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import { deepMerge } from "@/utils/deep-merge";

/** File extensions that support structured merge (JSON/JSONC and TOML). */
const MERGEABLE_EXTENSIONS = new Set([".json", ".jsonc", ".toml"]);

function isMergeable(configFile: string): boolean {
  return MERGEABLE_EXTENSIONS.has(extname(configFile));
}

/**
 * Strip single-line (`//`) and block (`/* ... *\/`) comments from a JSONC
 * string, respecting string literals so URLs and embedded slashes are safe.
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
      // Skip until end of line
      while (i < text.length && text[i] !== "\n") i++;
      if (i < text.length) result += "\n";
      continue;
    }
    if (!inString && ch === "/" && text[i + 1] === "*") {
      // Skip block comment
      i += 2;
      while (i < text.length && !(text[i] === "*" && text[i + 1] === "/")) i++;
      i++; // skip the closing /
      continue;
    }
    result += ch;
  }
  return result;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Parse a config file into a plain object based on its extension.
 * Returns `null` if the format is not supported for merge or parsing fails.
 */
function parseForMerge(
  content: string,
  configFile: string
): Record<string, unknown> | null {
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
}

/**
 * Serialize a plain object back to a string based on the config file extension.
 */
function serializeForMerge(data: Record<string, unknown>, configFile: string): string {
  const ext = extname(configFile);
  if (ext === ".toml") {
    return stringifyToml(data);
  }
  // JSON and JSONC: emit standard JSON (comments are not preserved)
  return JSON.stringify(data, null, 2);
}

async function applyStrategy(
  projectDir: string,
  configFile: string,
  generated: string,
  strategy: ConfigStrategy,
  fileManager: FileManager
): Promise<string | null> {
  const dest = join(projectDir, configFile);
  const exists = await fileManager.exists(dest);

  if (!exists) {
    return generated;
  }

  if (strategy === "skip") {
    return null;
  }

  if (strategy === "replace") {
    return generated;
  }

  // strategy === "merge"
  if (!isMergeable(configFile)) {
    // Cannot merge non-structured formats — fall back to replace
    return generated;
  }

  const existingText = await fileManager.readText(dest);
  const existingData = parseForMerge(existingText, configFile);
  const generatedData = parseForMerge(generated, configFile);

  if (existingData === null || generatedData === null) {
    // Parsing failed — fall back to replace
    return generated;
  }

  const merged = deepMerge(existingData, generatedData);
  return serializeForMerge(merged, configFile);
}

async function runGenerator(
  projectDir: string,
  fileManager: FileManager,
  id: string,
  configFile: string,
  generate: () => string,
  strategy: ConfigStrategy
): Promise<{ file: string; skipped?: true } | { error: string }> {
  try {
    const generated = generate();
    const content = await applyStrategy(
      projectDir,
      configFile,
      generated,
      strategy,
      fileManager
    );

    if (content === null) {
      return { file: configFile, skipped: true };
    }

    const dest = join(projectDir, configFile);
    await fileManager.mkdir(dirname(dest), { parents: true });
    await fileManager.writeText(dest, content);
    return { file: configFile };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { error: `${id}: ${message}` };
  }
}

export async function generateConfigsStep(
  projectDir: string,
  languages: readonly LanguagePlugin[],
  config: ResolvedConfig,
  fileManager: FileManager,
  strategy: ConfigStrategy = "merge"
): Promise<StepResult> {
  const results = await Promise.all(
    ALL_GENERATORS.map((g) => {
      const generate =
        g.id === lefthookGenerator.id
          ? () => generateLefthookConfig(config, languages)
          : () => g.generate(config);
      return runGenerator(
        projectDir,
        fileManager,
        g.id,
        g.configFile,
        generate,
        strategy
      );
    })
  );

  const written: string[] = [];
  const skipped: string[] = [];
  const errors: string[] = [];
  for (const r of results) {
    if ("error" in r) {
      errors.push(r.error);
    } else if (r.skipped === true) {
      skipped.push(r.file);
    } else {
      written.push(r.file);
    }
  }

  if (errors.length > 0) {
    return error(`Config generation failed: ${errors.join(", ")}`);
  }

  const parts: string[] = [];
  if (written.length > 0) {
    parts.push(`Generated ${written.length} config file(s): ${written.join(", ")}`);
  }
  if (skipped.length > 0) {
    parts.push(`Skipped ${skipped.length} existing file(s): ${skipped.join(", ")}`);
  }

  return ok(parts.join("; "));
}
