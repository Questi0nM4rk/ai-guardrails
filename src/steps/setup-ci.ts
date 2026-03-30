import { join } from "node:path";
import type { FileManager } from "@/infra/file-manager";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";

function buildCiWorkflow(languages: ReadonlySet<string>): string {
  const hasTs = languages.has("typescript");
  const hasPython = languages.has("python");

  const steps: string[] = [];
  steps.push("      - uses: actions/checkout@v4");

  // Bun is always needed for universal tools (markdownlint-cli2 via bunx)
  steps.push("      - uses: oven-sh/setup-bun@v2");
  if (hasPython) {
    steps.push("      - uses: actions/setup-python@v5");
    steps.push("        with:");
    steps.push('          python-version: "3.12"');
  }

  // Install dependencies
  if (hasTs) {
    steps.push("      - name: Install JS dependencies");
    steps.push("        run: bun install --frozen-lockfile");
    steps.push("        if: hashFiles('bun.lock', 'bun.lockb') != ''");
  }

  // pip installs: Python tools + codespell (always needed)
  const pipPackages: string[] = ["codespell"];
  if (hasPython) pipPackages.unshift("ruff", "pyright");
  const pipStepName = hasPython ? "Install Python tools" : "Install codespell";
  steps.push(`      - name: ${pipStepName}`);
  steps.push(`        run: pip install ${pipPackages.join(" ")}`);

  // Language-specific checks
  if (hasTs) {
    steps.push("      - name: Lint (biome)");
    steps.push("        run: bunx biome check .");
    steps.push("      - name: Typecheck (tsc)");
    steps.push("        run: bunx tsc --noEmit");
  }
  if (hasPython) {
    steps.push("      - name: Lint (ruff)");
    steps.push("        run: ruff check .");
    steps.push("      - name: Typecheck (pyright)");
    steps.push("        run: pyright");
  }

  // Universal checks (always)
  steps.push("      - name: Spell check");
  steps.push('        run: codespell --skip="*.lock,node_modules,dist" .');
  steps.push("      - name: Markdown lint");
  steps.push('        run: bunx markdownlint-cli2 "**/*.md" "#node_modules"');
  steps.push("      - name: Secret scan");
  steps.push("        uses: gitleaks/gitleaks-action@v2");
  steps.push("        env:");
  // biome-ignore lint/suspicious/noTemplateCurlyInString: GitHub Actions expression syntax, not JS template
  steps.push("          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}");

  return `name: AI Guardrails Check
on:
  push:
    branches: ["**"]
  pull_request:
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
${steps.join("\n")}
`;
}

export async function setupCiStep(
  projectDir: string,
  fileManager: FileManager,
  languages: ReadonlySet<string>
): Promise<StepResult> {
  try {
    const workflowDir = join(projectDir, ".github", "workflows");
    await fileManager.mkdir(workflowDir, { parents: true });

    const dest = join(workflowDir, "ai-guardrails.yml");
    await fileManager.writeText(dest, buildCiWorkflow(languages));

    return ok("CI workflow written to .github/workflows/ai-guardrails.yml");
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return error(`CI setup failed: ${message}`);
  }
}
