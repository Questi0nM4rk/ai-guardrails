import { describe, expect, test } from "bun:test";
import { parseWorkflowJobNames } from "@/utils/parse-workflow-jobs";
import { FakeFileManager } from "../fakes/fake-file-manager";

// FakeFileManager.glob matches seeded keys against the pattern directly.
// Using projectDir="" so join("", relative) === relative, matching seeded keys.
const PROJECT_DIR = "";

describe("parseWorkflowJobNames", () => {
  test("parses job names from workflow when name fields are present", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      ".github/workflows/ci.yml",
      `
on: [push]
jobs:
  check:
    name: "Test & Coverage"
    runs-on: ubuntu-latest
    steps: []
  lint:
    name: "Lint & Static Analysis"
    runs-on: ubuntu-latest
    steps: []
`
    );

    const names = await parseWorkflowJobNames(PROJECT_DIR, fm);

    expect(names).toContain("Test & Coverage");
    expect(names).toContain("Lint & Static Analysis");
  });

  test("falls back to job keys when no name is set", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      ".github/workflows/ci.yml",
      `
on: [push]
jobs:
  check:
    runs-on: ubuntu-latest
    steps: []
  build:
    runs-on: ubuntu-latest
    steps: []
`
    );

    const names = await parseWorkflowJobNames(PROJECT_DIR, fm);

    expect(names).toContain("check");
    expect(names).toContain("build");
  });

  test("handles multiple workflow files", async () => {
    const fm = new FakeFileManager();
    fm.seed(
      ".github/workflows/ci.yml",
      `
on: [push]
jobs:
  check:
    name: "CI Check"
    runs-on: ubuntu-latest
    steps: []
`
    );
    fm.seed(
      ".github/workflows/release.yml",
      `
on: [push]
jobs:
  publish:
    name: "Publish Release"
    runs-on: ubuntu-latest
    steps: []
`
    );

    const names = await parseWorkflowJobNames(PROJECT_DIR, fm);

    expect(names).toContain("CI Check");
    expect(names).toContain("Publish Release");
  });

  test("returns empty array when no workflow files exist", async () => {
    const fm = new FakeFileManager();

    const names = await parseWorkflowJobNames(PROJECT_DIR, fm);

    expect(names).toEqual([]);
  });
});
