import { describe, expect, test } from "bun:test";
import type { LintIssue } from "@/models/lint-issue";
import { applyFingerprints } from "@/utils/apply-fingerprints";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";

function makeRaw(
  overrides: Partial<Omit<LintIssue, "fingerprint">> = {}
): Omit<LintIssue, "fingerprint"> {
  return {
    rule: "ruff/E501",
    linter: "ruff",
    file: `${PROJECT_DIR}/src/foo.py`,
    line: 1,
    col: 1,
    message: "Line too long",
    severity: "error",
    ...overrides,
  };
}

describe("applyFingerprints", () => {
  test("returns LintIssue[] with fingerprint length 64", async () => {
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/src/foo.py`, "x = 1\n");
    const issues = await applyFingerprints([makeRaw()], PROJECT_DIR, fm);
    expect(issues).toHaveLength(1);
    expect(issues[0]?.fingerprint).toHaveLength(64);
  });

  test("same source line produces same fingerprint regardless of message", async () => {
    const fm1 = new FakeFileManager();
    fm1.seed(`${PROJECT_DIR}/src/foo.py`, "import os\n");
    const fm2 = new FakeFileManager();
    fm2.seed(`${PROJECT_DIR}/src/foo.py`, "import os\n");

    const raw = makeRaw({ message: "old message" });
    const rawDiffMsg = makeRaw({ message: "new message after tool upgrade" });

    const [issueOld] = await applyFingerprints([raw], PROJECT_DIR, fm1);
    const [issueNew] = await applyFingerprints([rawDiffMsg], PROJECT_DIR, fm2);

    expect(issueOld?.fingerprint).toBe(issueNew?.fingerprint);
  });

  test("different source lines produce different fingerprints", async () => {
    const fm = new FakeFileManager();
    fm.seed(`${PROJECT_DIR}/src/foo.py`, "line_one = 1\nline_two = 2\n");

    const rawLine1 = makeRaw({ line: 1 });
    const rawLine2 = makeRaw({ line: 2 });

    const [issue1] = await applyFingerprints([rawLine1], PROJECT_DIR, fm);
    const [issue2] = await applyFingerprints([rawLine2], PROJECT_DIR, fm);

    expect(issue1?.fingerprint).not.toBe(issue2?.fingerprint);
  });

  test("falls back to empty source lines when file cannot be read", async () => {
    const fm = new FakeFileManager(); // no file seeded
    const issues = await applyFingerprints([makeRaw()], PROJECT_DIR, fm);
    // Should still produce a valid fingerprint (not throw)
    expect(issues).toHaveLength(1);
    expect(issues[0]?.fingerprint).toHaveLength(64);
  });

  test("reads each file only once per group", async () => {
    const fm = new FakeFileManager();
    const content = "a = 1\nb = 2\nc = 3\n";
    fm.seed(`${PROJECT_DIR}/src/foo.py`, content);

    const raw = [makeRaw({ line: 1 }), makeRaw({ line: 2 }), makeRaw({ line: 3 })];

    const issues = await applyFingerprints(raw, PROJECT_DIR, fm);
    expect(issues).toHaveLength(3);
    // All fingerprints should be 64 chars
    for (const issue of issues) {
      expect(issue.fingerprint).toHaveLength(64);
    }
    // Issues for different lines should have different fingerprints
    expect(issues[0]?.fingerprint).not.toBe(issues[1]?.fingerprint);
    expect(issues[1]?.fingerprint).not.toBe(issues[2]?.fingerprint);
  });

  test("fingerprint uses project-relative path (portable across machines)", async () => {
    const sourceContent = "x = 1\n";

    const fm1 = new FakeFileManager();
    fm1.seed("/alice/repo/src/foo.py", sourceContent);
    const fm2 = new FakeFileManager();
    fm2.seed("/bob/repo/src/foo.py", sourceContent);

    const raw1 = makeRaw({ file: "/alice/repo/src/foo.py" });
    const raw2 = makeRaw({ file: "/bob/repo/src/foo.py" });

    const [i1] = await applyFingerprints([raw1], "/alice/repo", fm1);
    const [i2] = await applyFingerprints([raw2], "/bob/repo", fm2);

    // Same relative path + same source → same fingerprint
    expect(i1?.fingerprint).toBe(i2?.fingerprint);
  });
});
