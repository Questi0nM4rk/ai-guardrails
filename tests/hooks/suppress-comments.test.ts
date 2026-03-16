import { describe, expect, test } from "bun:test";
import { extractComment, scanFile } from "@/hooks/suppress-comments";

describe("scanFile", () => {
  // -----------------------------------------------------------------------
  // Language detection via extension
  // -----------------------------------------------------------------------
  test("detects shellcheck disable in .sh files", () => {
    const findings = scanFile("script.sh", "# shellcheck disable=SC2086\necho $var\n");
    expect(findings).toHaveLength(1);
    expect(findings[0]?.line).toBe(1);
  });

  test("detects shellcheck disable in .bash files", () => {
    const findings = scanFile("script.bash", "# shellcheck disable=SC2034\nx=1\n");
    expect(findings).toHaveLength(1);
  });

  test("detects shellcheck disable in .zsh files", () => {
    const findings = scanFile("config.zsh", "# shellcheck disable=SC2148\nx=1\n");
    expect(findings).toHaveLength(1);
  });

  test("detects shellcheck disable in .ksh files", () => {
    // Fix 7: .ksh was missing from EXT_TO_LANG
    const findings = scanFile("script.ksh", "# shellcheck disable=SC2086\necho $var\n");
    expect(findings).toHaveLength(1);
    expect(findings[0]?.line).toBe(1);
  });

  test("returns no findings for .ksh file without suppressions", () => {
    const findings = scanFile("script.ksh", "echo hello\n");
    expect(findings).toHaveLength(0);
  });

  test("returns no findings for unknown extension", () => {
    const findings = scanFile("data.csv", "# noqa\n");
    expect(findings).toHaveLength(0);
  });

  // -----------------------------------------------------------------------
  // Allow-comment bypass
  // -----------------------------------------------------------------------
  test("skips lines containing ai-guardrails-allow", () => {
    const findings = scanFile(
      "script.sh",
      '# shellcheck disable=SC2086  # ai-guardrails-allow: shellcheck/SC2086 "intentional"\n'
    );
    expect(findings).toHaveLength(0);
  });

  // -----------------------------------------------------------------------
  // Python suppression patterns
  // -----------------------------------------------------------------------
  test("detects # noqa in .py files", () => {
    const findings = scanFile("module.py", "x = 1  # noqa\n");
    expect(findings).toHaveLength(1);
  });

  test("detects # type: ignore in .py files", () => {
    const findings = scanFile("module.py", "x: int = 'bad'  # type: ignore\n");
    expect(findings).toHaveLength(1);
  });

  // -----------------------------------------------------------------------
  // nosemgrep detection
  // -----------------------------------------------------------------------
  test("detects nosemgrep in TypeScript files", () => {
    const findings = scanFile("file.ts", "new RegExp(x); // nosemgrep: some-rule\n");
    expect(findings).toHaveLength(1);
    expect(findings[0]?.pattern).toBe("nosemgrep");
  });

  // -----------------------------------------------------------------------
  // Generic comment-only keyword scanner
  // -----------------------------------------------------------------------
  test("generic scanner catches NOLINT in TypeScript comment", () => {
    const findings = scanFile("file.ts", "code(); // NOLINT\n");
    expect(findings).toHaveLength(1);
    expect(findings[0]?.pattern).toBe("generic-suppression-keyword");
  });

  test("generic scanner does not flag keywords in code", () => {
    const findings = scanFile("file.ts", "const suppressWarning = true;\n");
    expect(findings).toHaveLength(0);
  });

  test("generic scanner flags suppress-lint in comment", () => {
    const findings = scanFile("file.ts", "code(); // suppress-lint\n");
    expect(findings).toHaveLength(1);
    expect(findings[0]?.pattern).toBe("generic-suppression-keyword");
  });

  test("generic scanner skips lines with ai-guardrails-allow", () => {
    const findings = scanFile(
      "file.ts",
      '// nosemgrep: rule // ai-guardrails-allow: semgrep/rule "justified"\n'
    );
    expect(findings).toHaveLength(0);
  });

  test("generic scanner does not double-flag explicit pattern hits", () => {
    // nosemgrep is an explicit pattern — should only appear once
    const findings = scanFile("file.ts", "new RegExp(x); // nosemgrep: rule\n");
    expect(findings).toHaveLength(1);
    expect(findings[0]?.pattern).toBe("nosemgrep");
  });
});

describe("extractComment", () => {
  test("extracts // comment", () => {
    expect(extractComment("const x = 1; // some comment")).toBe(" some comment");
  });

  test("extracts # comment", () => {
    expect(extractComment("x = 1  # noqa")).toBe(" noqa");
  });

  test("extracts -- comment", () => {
    expect(extractComment("local x = 1 -- luacheck: ignore")).toBe(" luacheck: ignore");
  });

  test("extracts block comment", () => {
    expect(extractComment("x = 1; /* suppress */")).toBe(" suppress ");
  });

  test("returns empty for no comment", () => {
    expect(extractComment("const x = 1;")).toBe("");
  });
});
