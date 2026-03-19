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
  if (typeof packageJson !== "object" || packageJson === null) return "warn";

  const pkg = packageJson as Record<string, unknown>;

  const deps =
    typeof pkg.dependencies === "object" && pkg.dependencies !== null
      ? (pkg.dependencies as Record<string, unknown>)
      : {};
  const devDeps =
    typeof pkg.devDependencies === "object" && pkg.devDependencies !== null
      ? (pkg.devDependencies as Record<string, unknown>)
      : {};
  const allDeps = { ...deps, ...devDeps };

  // Browser frameworks take precedence over CLI detection
  if (BROWSER_FRAMEWORKS.some((f) => f in allDeps)) return "error";

  // CLI tools — only if no browser framework was found
  if ("bin" in pkg) return "off";

  return "warn";
}
