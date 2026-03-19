import { z } from "zod";

export type NoConsoleLevel = "off" | "warn" | "error";

const BROWSER_FRAMEWORKS = [
  "react",
  "vue",
  "svelte",
  "@angular/core",
  "next",
  "nuxt",
  "solid-js",
  "preact",
  "qwik",
] as const;

/** Loose schema for package.json — only validates the fields we care about */
const PackageJsonSchema = z
  .object({
    bin: z.unknown().optional(),
    dependencies: z.record(z.unknown()).optional(),
    devDependencies: z.record(z.unknown()).optional(),
  })
  .passthrough();

/**
 * Detect the appropriate noConsole level based on package.json content.
 *
 * Browser frameworks → "error" (console is debugging noise)
 * CLI tools (bin field present) → "off" (console is the output mechanism)
 * Everything else → "warn" (server, library, or unknown)
 *
 * Browser wins over CLI: if both bin and react exist → "error"
 */
export function detectNoConsoleLevel(packageJson: unknown): NoConsoleLevel {
  const parsed = PackageJsonSchema.safeParse(packageJson);
  if (!parsed.success) return "warn";

  const { bin, dependencies, devDependencies } = parsed.data;
  const allDeps = { ...dependencies, ...devDependencies };

  // Browser frameworks take precedence over CLI detection
  if (BROWSER_FRAMEWORKS.some((f) => f in allDeps)) return "error";

  // CLI tools — only if no browser framework was found
  if (bin !== undefined) return "off";

  return "warn";
}
