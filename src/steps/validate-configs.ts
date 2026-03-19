import { join } from "node:path";
import { ALL_GENERATORS, applicableGenerators } from "@/generators/registry";
import type { ConfigGenerator } from "@/generators/types";
import type { FileManager } from "@/infra/file-manager";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import { computeHash } from "@/utils/hash";

const HASH_HEADER_PATTERN =
  /^(?:\/\/|#) ai-guardrails:sha256=([0-9a-f]{64})$|^<!-- ai-guardrails:sha256=([0-9a-f]{64}) -->$/;

function hasValidHash(content: string): boolean {
  const firstNewline = content.indexOf("\n");
  if (firstNewline === -1) return false;
  const headerLine = content.slice(0, firstNewline);
  const rest = content.slice(firstNewline + 1);
  const match = HASH_HEADER_PATTERN.exec(headerLine);
  const storedHash = match?.[1] ?? match?.[2];
  if (!storedHash) return false;
  return computeHash(rest) === storedHash;
}

function hasHashHeader(content: string): boolean {
  const firstNewline = content.indexOf("\n");
  if (firstNewline === -1) return false;
  const headerLine = content.slice(0, firstNewline);
  return HASH_HEADER_PATTERN.test(headerLine);
}

async function validateOne(
  generator: ConfigGenerator,
  projectDir: string,
  fileManager: FileManager
): Promise<string | null> {
  let content: string;
  try {
    content = await fileManager.readText(join(projectDir, generator.configFile));
  } catch {
    return `missing: ${generator.configFile}`;
  }

  if (!content.trim()) return `empty: ${generator.configFile}`;

  // Tamper check: verify hash header matches body.
  // Files with no header are user-owned and not tamper-checked.
  // Files with a valid hash were written by us (generated or merged) and are intact.
  // Files with a header but invalid hash have been manually edited after generation.
  if (hasHashHeader(content) && !hasValidHash(content)) {
    return `tampered: ${generator.configFile}`;
  }

  // Staleness detection (comparing on-disk content against fresh generation) is
  // intentionally not implemented here. Merged files also receive a valid hash header
  // (withHashHeader is applied after merge), so we cannot distinguish a purely
  // generated file from a merged one by hash alone. Comparing a merged file against
  // generator.generate() would always report "stale". Staleness detection requires
  // provenance tracking (recording whether each file was merged or replaced at
  // generation time) which is deferred to a future phase.

  return null;
}

/**
 * Validate config files that were actually generated.
 * When activeLanguageIds is provided, only validates generators applicable
 * to those languages (matching the language-gate filter in generate-configs).
 */
export async function validateConfigsStep(
  projectDir: string,
  fileManager: FileManager,
  activeLanguageIds?: ReadonlySet<string>
): Promise<StepResult> {
  const generators =
    activeLanguageIds !== undefined
      ? applicableGenerators(activeLanguageIds)
      : ALL_GENERATORS;

  const problems = (
    await Promise.all(generators.map((g) => validateOne(g, projectDir, fileManager)))
  ).filter((p): p is string => p !== null);

  if (problems.length > 0) {
    return error(`Config validation failed: ${problems.join(", ")}`);
  }

  return ok(`All ${generators.length} config files validated`);
}
