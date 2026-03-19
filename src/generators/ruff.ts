import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import { withHashHeader } from "@/utils/hash";

function renderRuffToml(config: ResolvedConfig): string {
  const lineLength = config.values.line_length ?? 88;
  const indentWidth = config.values.indent_width ?? 4;
  const content = `target-version = "py311"
line-length = ${lineLength}
indent-width = ${indentWidth}
fix = false
unsafe-fixes = false

[lint]
select = ["ALL"]

ignore = [
  # --- Formatter conflicts ---
  "W191", "E111", "E114", "E117", "D206", "D300",
  "Q000", "Q001", "Q002", "Q003", "COM812", "COM819",
  "ISC001", "ISC002",
  # --- Redundant with pyright ---
  "ANN",
  # --- Docstrings (opt-in) ---
  "D",
  # --- Development markers ---
  "FIX001", "FIX002", "TD",
  # --- High false-positive ---
  "ERA001", "CPY001", "INP001", "T201",
  "EM101", "EM102", "TRY003", "S101",
]

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

[lint.mccabe]
max-complexity = 10

[lint.pylint]
max-args = 5
max-branches = 10
max-locals = 10
max-statements = 30

[format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "lf"
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
