import { join } from "node:path";
import { buildContext } from "@/commands/context";
import { loadProjectConfig } from "@/config/loader";

/**
 * ai-guardrails query <rule>
 *
 * Shows all files where the given rule is allowed:
 *   - Config-level: [[allow]] entries in config.toml
 *   - Inline: ai-guardrails-allow comments in source files
 */
export async function runQuery(projectDir: string, rule: string): Promise<void> {
  const ctx = buildContext(projectDir, {});
  const { fileManager, console: cons } = ctx;

  // --- Config-level allows ---
  const project = await loadProjectConfig(projectDir, fileManager);
  const configMatches = project.allow.filter((entry) => entry.rule === rule);

  if (configMatches.length > 0) {
    cons.info(`Config-level allows for ${rule}:`);
    for (const entry of configMatches) {
      cons.info(`  glob: ${entry.glob}  reason: "${entry.reason}"`);
    }
  } else {
    cons.info(`No config-level allows for ${rule}`);
  }

  // --- Inline allows: scan all source files ---
  const allFiles = await fileManager.glob("**/*", projectDir, [
    "node_modules/**",
    ".git/**",
    "dist/**",
  ]);

  const ALLOW_RE = /ai-guardrails-allow\s+([\w-]+\/[\w\-.]+)\s+"([^"]+)"/;

  const inlineMatches: Array<{ file: string; line: number; reason: string }> = [];

  await Promise.all(
    allFiles.map(async (relativePath) => {
      const absPath = join(projectDir, relativePath);
      let source: string;
      try {
        source = await fileManager.readText(absPath);
      } catch {
        return;
      }
      const lines = source.split("\n");
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line === undefined) continue;
        const match = ALLOW_RE.exec(line);
        if (match !== null && match[1] === rule) {
          const reason = match[2] ?? "";
          inlineMatches.push({ file: relativePath, line: i + 1, reason });
        }
      }
    })
  );

  if (inlineMatches.length > 0) {
    cons.info(`\nInline allows for ${rule}:`);
    for (const m of inlineMatches) {
      cons.info(`  ${m.file}:${m.line}  reason: "${m.reason}"`);
    }
  } else {
    cons.info(`No inline allows for ${rule}`);
  }

  if (configMatches.length === 0 && inlineMatches.length === 0) {
    cons.info(`\nRule "${rule}" is not suppressed anywhere.`);
  }
}
