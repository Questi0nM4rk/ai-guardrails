import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import { withHashHeader } from "@/utils/hash";

const RUFF_SELECT_BY_PROFILE = {
  strict: `["ALL"]`,
  standard: `["E", "F", "W", "I", "UP", "S", "B", "A", "C4", "ICN", "PIE", "PT", "RSE", "SIM", "TID"]`,
  minimal: `["E", "F", "S"]`,
} as const satisfies Record<"strict" | "standard" | "minimal", string>;

/**
 * Rules removed from the ignore list for strict profile — they are enforced
 * strictly and should not be silenced.
 */
const RUFF_STRICT_UNENFORCE = new Set(["T201", "S101", "ERA001"]);

const BASE_IGNORE_RULES = [
  // --- Formatter conflicts ---
  "W191",
  "E111",
  "E114",
  "E117",
  "D206",
  "D300",
  "Q000",
  "Q001",
  "Q002",
  "Q003",
  "COM812",
  "COM819",
  "ISC001",
  "ISC002",
  // --- Redundant with pyright ---
  "ANN",
  // --- Docstrings (opt-in) ---
  "D",
  // --- Development markers ---
  "FIX001",
  "FIX002",
  "TD",
  // --- High false-positive ---
  "ERA001",
  "CPY001",
  "INP001",
  "T201",
  "EM101",
  "EM102",
  "TRY003",
  "S101",
] as const;

function buildIgnoreList(profile: "strict" | "standard" | "minimal"): string {
  const rules =
    profile === "strict"
      ? BASE_IGNORE_RULES.filter((r) => !RUFF_STRICT_UNENFORCE.has(r))
      : [...BASE_IGNORE_RULES];

  const quoted = rules.map((r) => `"${r}"`).join(", ");
  return `[${quoted}]`;
}

function renderRuffToml(config: ResolvedConfig): string {
  const lineLength = config.values.line_length ?? 88;
  const indentWidth = config.values.indent_width ?? 4;
  const selectRules = RUFF_SELECT_BY_PROFILE[config.profile];
  const ignoreRules = buildIgnoreList(config.profile);

  const content = `target-version = "py311"
line-length = ${lineLength}
indent-width = ${indentWidth}
fix = false
unsafe-fixes = false

[lint]
select = ${selectRules}

ignore = ${ignoreRules}

[lint.per-file-ignores]
"tests/**/*.py" = ["ARG001", "ARG002", "PLR2004"]
"**/__init__.py" = ["F401"]

[lint.pydocstyle]
convention = "google"

[lint.flake8-type-checking]
strict = true
runtime-evaluated-base-classes = ["pydantic.BaseModel"]

[lint.isort]
force-single-line = false
force-sort-within-sections = true
combine-as-imports = true
split-on-trailing-comma = true
force-to-top = ["__future__"]
required-imports = ["from __future__ import annotations"]

[lint.flake8-tidy-imports]
ban-relative-imports = "all"

[lint.flake8-tidy-imports.banned-api]
"typing.Optional".msg = "Use \`X | None\` instead"
"typing.Union".msg   = "Use \`X | Y\` instead"
"typing.List".msg    = "Use \`list[X]\` instead"
"typing.Dict".msg    = "Use \`dict[X, Y]\` instead"
"typing.Set".msg     = "Use \`set[X]\` instead"
"typing.Tuple".msg   = "Use \`tuple[X, ...]\` instead"

[lint.mccabe]
max-complexity = 10

[lint.pylint]
max-args = 5
max-bool-expr = 3
max-branches = 10
max-locals = 10
max-nested-blocks = 3
max-positional-args = 5
max-public-methods = 15
max-returns = 4
max-statements = 30

[lint.flake8-bugbear]
extend-immutable-calls = ["fastapi.Depends", "fastapi.Query", "fastapi.Path"]

[lint.flake8-quotes]
inline-quotes = "double"
multiline-quotes = "double"
docstring-quotes = "double"

[lint.flake8-pytest-style]
fixture-parentheses = true
mark-parentheses = true
parametrize-names-type = "csv"
parametrize-values-type = "list"
raises-require-match-for = ["ValueError", "TypeError", "KeyError", "RuntimeError"]

[format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "lf"
docstring-code-format = true
docstring-code-line-length = 80
`;
  return withHashHeader(content);
}

export const ruffGenerator: ConfigGenerator = {
  id: "ruff",
  configFile: "ruff.toml",
  languages: ["python"],
  generate(config: ResolvedConfig): string {
    return renderRuffToml(config);
  },
};
