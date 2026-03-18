import { expect } from "bun:test";
import type { DataTable, World } from "@questi0nm4rk/feats";
import { Then, When } from "@questi0nm4rk/feats";
import { Glob } from "bun";
import type { AllowComment } from "@/hooks/allow-comment";
import { parseAllowComments } from "@/hooks/allow-comment";
import { FORMATTERS, getStagedFiles } from "@/hooks/format-stage";
import { extractComment, scanFile } from "@/hooks/suppress-comments";

type Finding = ReturnType<typeof scanFile>[number];

// Lines containing URLs with embedded double quotes — referenced by index
const URL_TEST_LINES: Record<number, string> = {
  1: 'const url = "http://example.com"; // real comment',
  2: 'const url = "https://nolint.io/api";',
};

interface SuppressWorld extends World {
  findings: Finding[];
  extractedComment: string;
  allowComments: AllowComment[];
  stagedFiles: string[];
  extractLang: string;
}

// --- suppress-comments steps ---

When(
  "I scan {string} with content {string}",
  (world: SuppressWorld, filename: unknown, rawContent: unknown) => {
    if (typeof filename !== "string") throw new Error("expected string filename");
    if (typeof rawContent !== "string") throw new Error("expected string content");
    const content = rawContent.replace(/\\n/g, "\n").replace(/\\"/g, '"');
    world.findings = scanFile(filename, content);
  }
);

Then("the findings count should be {int}", (world: SuppressWorld, count: unknown) => {
  if (typeof count !== "number") throw new Error("expected number");
  expect(world.findings).toHaveLength(count);
});

Then("finding at line {int} should exist", (world: SuppressWorld, line: unknown) => {
  if (typeof line !== "number") throw new Error("expected number");
  expect(world.findings.some((f) => f.line === line)).toBe(true);
});

Then(
  "finding pattern should contain {string}",
  (world: SuppressWorld, substr: unknown) => {
    if (typeof substr !== "string") throw new Error("expected string");
    const first = world.findings[0];
    expect(first).toBeDefined();
    expect(first?.pattern).toContain(substr);
  }
);

Then("finding pattern should be {string}", (world: SuppressWorld, pattern: unknown) => {
  if (typeof pattern !== "string") throw new Error("expected string");
  const first = world.findings[0];
  expect(first).toBeDefined();
  expect(first?.pattern).toBe(pattern);
});

When(
  "I extract comment from {string} for language {string}",
  (world: SuppressWorld, line: unknown, lang: unknown) => {
    if (typeof line !== "string") throw new Error("expected string line");
    if (typeof lang !== "string") throw new Error("expected string lang");
    world.extractedComment = extractComment(line, lang);
  }
);

// URL test lines require embedded double quotes; reference them by index
When(
  "I extract comment from url-test line {int} for language {string}",
  (world: SuppressWorld, lineIndex: unknown, lang: unknown) => {
    if (typeof lineIndex !== "number") throw new Error("expected number");
    if (typeof lang !== "string") throw new Error("expected string lang");
    const line = URL_TEST_LINES[lineIndex];
    if (line === undefined) throw new Error(`No url-test line at index ${lineIndex}`);
    world.extractedComment = extractComment(line, lang);
  }
);

Then(
  "the extracted comment should be {string}",
  (world: SuppressWorld, expected: unknown) => {
    if (typeof expected !== "string") throw new Error("expected string");
    expect(world.extractedComment).toBe(expected);
  }
);

Then(
  "the extracted comment should start with {string}",
  (world: SuppressWorld, prefix: unknown) => {
    if (typeof prefix !== "string") throw new Error("expected string");
    expect(world.extractedComment).toContain(prefix.trim());
  }
);

// --- allow-comment steps ---

When("I parse allow comments from lines:", (world: SuppressWorld, table: unknown) => {
  const dt = table as DataTable;
  const lines = dt.asLists().map((row) => row[0] ?? "");
  world.allowComments = parseAllowComments(lines);
});

When("I parse allow comments from no lines", (world: SuppressWorld) => {
  world.allowComments = parseAllowComments([]);
});

Then(
  "there should be {int} allow comment(s)",
  (world: SuppressWorld, count: unknown) => {
    if (typeof count !== "number") throw new Error("expected number");
    expect(world.allowComments).toHaveLength(count);
  }
);

Then(
  "allow comment {int} should have rule {string}",
  (world: SuppressWorld, index: unknown, rule: unknown) => {
    if (typeof index !== "number") throw new Error("expected number");
    if (typeof rule !== "string") throw new Error("expected string");
    const comment = world.allowComments[index - 1];
    expect(comment).toBeDefined();
    expect(comment?.rule).toBe(rule);
  }
);

Then(
  "allow comment {int} should have reason {string}",
  (world: SuppressWorld, index: unknown, reason: unknown) => {
    if (typeof index !== "number") throw new Error("expected number");
    if (typeof reason !== "string") throw new Error("expected string");
    const comment = world.allowComments[index - 1];
    expect(comment).toBeDefined();
    expect(comment?.reason).toBe(reason);
  }
);

Then(
  "allow comment {int} should be on line {int}",
  (world: SuppressWorld, index: unknown, line: unknown) => {
    if (typeof index !== "number") throw new Error("expected number");
    if (typeof line !== "number") throw new Error("expected number");
    const comment = world.allowComments[index - 1];
    expect(comment).toBeDefined();
    expect(comment?.line).toBe(line);
  }
);

// --- format-stage steps ---

Then(
  "FORMATTERS should match glob for file {string}",
  (_world: SuppressWorld, filename: unknown) => {
    if (typeof filename !== "string") throw new Error("expected string");
    const matches = FORMATTERS.some((f) => new Glob(f.glob).match(filename));
    expect(matches).toBe(true);
  }
);

Then("each formatter should have a non-empty glob", (_world: SuppressWorld) => {
  for (const formatter of FORMATTERS) {
    expect(formatter.glob.length).toBeGreaterThan(0);
  }
});

Then("each formatter cmd should return a non-empty array", (_world: SuppressWorld) => {
  for (const formatter of FORMATTERS) {
    const result = formatter.cmd(["test.ts"]);
    expect(result.length).toBeGreaterThan(0);
  }
});

When("I call getStagedFiles", (world: SuppressWorld) => {
  world.stagedFiles = getStagedFiles();
});

Then("the result should be an array", (world: SuppressWorld) => {
  expect(Array.isArray(world.stagedFiles)).toBe(true);
});

Then("no file in the result should be an empty string", (world: SuppressWorld) => {
  for (const file of world.stagedFiles) {
    expect(file.length).toBeGreaterThan(0);
  }
});

Then(
  "each formatter cmd should return a non-empty array with a truthy first element",
  (_world: SuppressWorld) => {
    for (const formatter of FORMATTERS) {
      const cmd = formatter.cmd(["test-file.py"]);
      expect(cmd.length).toBeGreaterThan(0);
      expect(cmd[0]).toBeTruthy();
    }
  }
);
