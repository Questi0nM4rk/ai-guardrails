import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import type { LanguagePlugin } from "@/languages/types";
import { withHashHeader } from "@/utils/hash";

/**
 * Convert a glob pattern to a regex string suitable for lefthook's `exclude` field.
 * Lefthook excludes accept a Go regex, not a glob.
 *
 * Conversion rules:
 * - `**` → `.*`
 * - `*` → `[^/]*`
 * - `.` → `\.`
 * - Other regex metacharacters are escaped
 */
function globToRegex(glob: string): string {
  // Escape regex metacharacters except `*` (handled separately)
  const escaped = glob.replace(/[.+^${}()|[\]\\?]/g, (ch) =>
    ch === "?" ? "[^/]" : `\\${ch}`
  );
  // Replace `**` before `*` to avoid double-processing
  return escaped.replace(/\*\*/g, ".*").replace(/\*/g, "[^/]*");
}

function buildExcludeRegex(ignorePaths: readonly string[]): string | undefined {
  if (ignorePaths.length === 0) return undefined;
  const parts = ignorePaths.map(globToRegex);
  return parts.length === 1 ? (parts[0] ?? "") : `(${parts.join("|")})`;
}

function renderLefthookYml(
  activePluginIds: ReadonlySet<string>,
  ignorePaths: readonly string[]
): string {
  const hasPython = activePluginIds.has("python");
  const hasTs = activePluginIds.has("typescript");
  const excludeRegex = buildExcludeRegex(ignorePaths);
  const excludeLine =
    excludeRegex !== undefined ? `\n      exclude: '${excludeRegex}'` : "";

  const pythonSection = hasPython
    ? `
    ruff-fix:
      glob: "*.py"${excludeLine}
      run: ruff check --fix {staged_files} && git add {staged_files}
      stage_fixed: true
      priority: 1
`
    : "";

  const tsSection = hasTs
    ? `
    biome-fix:
      glob: "*.{ts,tsx,js,jsx}"${excludeLine}
      run: biome check --write {staged_files} && git add {staged_files}
      stage_fixed: true
      priority: 1
`
    : "";

  return `pre-commit:
  commands:
${pythonSection}${tsSection}
    gitleaks:
      run: gitleaks protect --staged --no-banner
      fail_text: "Potential secrets detected"
      priority: 2

    codespell:
      glob: "*.{ts,md,txt,yaml,yml,toml,json,py,go,rs}"
      exclude: 'tests/fixtures/.*${excludeRegex !== undefined ? `|${excludeRegex}` : ""}'
      run: codespell --check-filenames {staged_files}
      fail_text: "Spell errors found"
      priority: 2

    markdownlint:
      glob: "*.md"${excludeLine}
      run: markdownlint-cli2 {staged_files}
      fail_text: "Markdown lint errors found"
      priority: 2

    check-suppress-comments:
      glob: "*.{py,ts,tsx,js,jsx,rs,go,cs,lua,sh,bash,zsh,ksh,c,cpp,cc,h,hpp}"${excludeLine}
      run: ai-guardrails hook suppress-comments {staged_files}
      fail_text: "Inline suppression comments require a reason"
      priority: 2

    no-commits-to-main:
      run: |
        branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
        if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
          echo "Direct commits to main are not allowed"
          exit 1
        fi
      fail_text: "Do not commit directly to main"
      priority: 2

commit-msg:
  commands:
    conventional:
      run: grep -qE "^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\\(.+\\))?!?:" {1}
      fail_text: "Commit message must follow Conventional Commits format"
`;
}

/**
 * Generate a lefthook.yml tailored to the active language plugins.
 * Callers must pass active plugin ids resolved from detectLanguages().
 */
export function generateLefthookConfig(
  config: ResolvedConfig,
  activePlugins: readonly LanguagePlugin[]
): string {
  const ids = new Set(activePlugins.map((p) => p.id));
  return withHashHeader(renderLefthookYml(ids, config.ignorePaths));
}

export const LEFTHOOK_GENERATOR_ID = "lefthook";

export const lefthookGenerator: ConfigGenerator = {
  id: LEFTHOOK_GENERATOR_ID,
  configFile: "lefthook.yml",
  generate(_config: ResolvedConfig): string {
    throw new Error(
      "lefthookGenerator.generate() must not be called directly — use generateLefthookConfig(config, languages) instead"
    );
  },
};
