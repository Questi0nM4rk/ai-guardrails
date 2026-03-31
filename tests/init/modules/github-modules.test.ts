import { describe, expect, test } from "bun:test";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { githubBranchProtectionModule } from "@/init/modules/github-branch-protection";
import { githubCcReviewerModule } from "@/init/modules/github-cc-reviewer";
import { githubPrTemplateModule } from "@/init/modules/github-pr-template";
import { githubProtectedPatternsModule } from "@/init/modules/github-protected-patterns";
import type { InitContext } from "@/init/types";
import { FakeCommandRunner } from "../../fakes/fake-command-runner";
import { FakeConsole } from "../../fakes/fake-console";
import { FakeFileManager } from "../../fakes/fake-file-manager";

function makeCtx(overrides?: Partial<InitContext>): InitContext {
  const config = buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse({})
  );
  return {
    projectDir: "/project",
    fileManager: new FakeFileManager(),
    commandRunner: new FakeCommandRunner(),
    console: new FakeConsole(),
    config,
    languages: [],
    selections: new Map(),
    isTTY: false,
    createReadline: () => ({
      question: (_q: string, cb: (a: string) => void) => cb(""),
      close: () => {},
    }),
    flags: {},
    github: { owner: "testowner", repo: "testrepo", authenticated: true },
    ...overrides,
  };
}

/** Returns an InitContext with no github field (exactOptionalPropertyTypes-safe). */
function makeCtxNoGithub(
  overrides?: Omit<Partial<InitContext>, "github">
): InitContext {
  const { github: _github, ...base } = makeCtx(overrides);
  return base;
}

// ---------------------------------------------------------------------------
// github-pr-template
// ---------------------------------------------------------------------------

describe("github-pr-template — writes template when absent", () => {
  test("creates pull_request_template.md", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.git", "");
    const ctx = makeCtx({ fileManager: fm });

    const result = await githubPrTemplateModule.execute(ctx);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("pull_request_template.md");
    const written = fm.written.find(([p]) => p.endsWith("pull_request_template.md"));
    expect(written).toBeDefined();
    const content = written?.[1] ?? "";
    expect(content).toContain("## Summary");
    expect(content).toContain("## Test plan");
    expect(content).toContain("## Notes");
    expect(result.filesCreated).toContain(".github/pull_request_template.md");
  });
});

describe("github-pr-template — skips when template exists", () => {
  test("returns skipped when file already present", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.git", "");
    fm.seed("/project/.github/pull_request_template.md", "# existing");
    const ctx = makeCtx({ fileManager: fm });

    const result = await githubPrTemplateModule.execute(ctx);

    expect(result.status).toBe("skipped");
    expect(fm.written.some(([p]) => p.endsWith("pull_request_template.md"))).toBe(
      false
    );
  });
});

describe("github-pr-template — detect", () => {
  test("returns false when .git is absent", async () => {
    const ctx = makeCtx();
    expect(await githubPrTemplateModule.detect(ctx)).toBe(false);
  });

  test("returns false when github is undefined", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.git", "");
    const ctx = makeCtxNoGithub({ fileManager: fm });
    expect(await githubPrTemplateModule.detect(ctx)).toBe(false);
  });

  test("returns true when .git exists and github is set", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.git", "");
    const ctx = makeCtx({ fileManager: fm });
    expect(await githubPrTemplateModule.detect(ctx)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// github-cc-reviewer
// ---------------------------------------------------------------------------

describe("github-cc-reviewer — writes .coderabbit.yaml", () => {
  test("creates config file with expected content", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.git", "");
    const ctx = makeCtx({ fileManager: fm });

    const result = await githubCcReviewerModule.execute(ctx);

    expect(result.status).toBe("ok");
    const written = fm.written.find(([p]) => p.endsWith(".coderabbit.yaml"));
    expect(written).toBeDefined();
    const content = written?.[1] ?? "";
    expect(content).toContain('language: "en-US"');
    expect(content).toContain("enable_free_tier: true");
    expect(content).toContain('profile: "auto"');
    expect(content).toContain("auto_reply: true");
    expect(result.filesCreated).toContain(".coderabbit.yaml");
  });
});

describe("github-cc-reviewer — skips when file exists", () => {
  test("returns skipped when .coderabbit.yaml already present", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.git", "");
    fm.seed("/project/.coderabbit.yaml", "# existing");
    const ctx = makeCtx({ fileManager: fm });

    const result = await githubCcReviewerModule.execute(ctx);

    expect(result.status).toBe("skipped");
    expect(fm.written.some(([p]) => p.endsWith(".coderabbit.yaml"))).toBe(false);
  });
});

describe("github-cc-reviewer — skips when not authenticated", () => {
  test("returns skipped when github.authenticated is false", async () => {
    const ctx = makeCtx({
      github: { owner: "testowner", repo: "testrepo", authenticated: false },
    });
    const result = await githubCcReviewerModule.execute(ctx);
    expect(result.status).toBe("skipped");
    expect(result.message).toContain("gh auth login");
  });

  test("returns skipped when github is undefined", async () => {
    const ctx = makeCtxNoGithub();
    const result = await githubCcReviewerModule.execute(ctx);
    expect(result.status).toBe("skipped");
  });
});

// ---------------------------------------------------------------------------
// github-branch-protection
// ---------------------------------------------------------------------------

describe("github-branch-protection — skips when not authenticated", () => {
  test("returns skipped when github is undefined", async () => {
    const ctx = makeCtxNoGithub();
    const result = await githubBranchProtectionModule.execute(ctx);
    expect(result.status).toBe("skipped");
  });

  test("returns skipped when authenticated is false", async () => {
    const ctx = makeCtx({
      github: { owner: "testowner", repo: "testrepo", authenticated: false },
    });
    const result = await githubBranchProtectionModule.execute(ctx);
    expect(result.status).toBe("skipped");
    expect(result.message).toContain("gh auth login");
  });
});

describe("github-branch-protection — calls gh api with correct args", () => {
  test("sends PUT to branches/main/protection with required fields", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.git", "");
    const cr = new FakeCommandRunner();
    // gh api succeeds
    cr.register(
      [
        "gh",
        "api",
        "repos/testowner/testrepo/branches/main/protection",
        "--method",
        "PUT",
        "--field",
        "required_status_checks[strict]=true",
        "--field",
        "enforce_admins=false",
        "--field",
        "required_pull_request_reviews[required_approving_review_count]=1",
        "--field",
        "required_pull_request_reviews[dismiss_stale_reviews]=true",
        "--field",
        "restrictions=null",
        "--field",
        "allow_force_pushes=false",
        "--field",
        "allow_deletions=false",
        "--field",
        "required_conversation_resolution=true",
      ],
      { stdout: "{}", stderr: "", exitCode: 0 }
    );
    const ctx = makeCtx({ fileManager: fm, commandRunner: cr });

    const result = await githubBranchProtectionModule.execute(ctx);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("Branch protection set on main");

    // Verify the call was made
    const call = cr.calls.find(
      (c) => c[0] === "gh" && c[2]?.includes("branches/main/protection")
    );
    expect(call).toBeDefined();
    expect(call).toContain("--method");
    expect(call).toContain("PUT");
    expect(call).toContain("allow_force_pushes=false");
  });

  test("includes workflow job names as status check contexts", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.git", "");
    // Seed at relative path so FakeFileManager.glob matches the pattern,
    // and at absolute path so readText succeeds after join(projectDir, file).
    const workflowContent = `jobs:\n  test:\n    name: "Test & Coverage"\n  lint:\n    name: "Lint & Static Analysis"\n`;
    fm.seed(".github/workflows/ci.yml", workflowContent);
    fm.seed("/project/.github/workflows/ci.yml", workflowContent);
    const cr = new FakeCommandRunner();
    const ctx = makeCtx({ fileManager: fm, commandRunner: cr });

    await githubBranchProtectionModule.execute(ctx);

    const call = cr.calls.find(
      (c) => c[0] === "gh" && c[2]?.includes("branches/main/protection")
    );
    expect(call).toBeDefined();
    // Should contain the job name fields
    const callStr = call?.join(" ") ?? "";
    expect(callStr).toContain("Test & Coverage");
    expect(callStr).toContain("Lint & Static Analysis");
  });

  test("handles 404 branch not found as skipped", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.git", "");
    const cr = new FakeCommandRunner();
    // All commands return 404
    const ctx = makeCtx({ fileManager: fm, commandRunner: cr });
    // No workflow files seeded — jobNames is empty, so required_status_checks=null
    cr.register(
      [
        "gh",
        "api",
        "repos/testowner/testrepo/branches/main/protection",
        "--method",
        "PUT",
        "--field",
        "required_status_checks=null",
        "--field",
        "enforce_admins=false",
        "--field",
        "required_pull_request_reviews[required_approving_review_count]=1",
        "--field",
        "required_pull_request_reviews[dismiss_stale_reviews]=true",
        "--field",
        "restrictions=null",
        "--field",
        "allow_force_pushes=false",
        "--field",
        "allow_deletions=false",
        "--field",
        "required_conversation_resolution=true",
      ],
      { stdout: "", stderr: "branch not found: 404", exitCode: 1 }
    );

    const result = await githubBranchProtectionModule.execute(ctx);

    expect(result.status).toBe("skipped");
    expect(result.message).toContain("first push to main");
  });
});

// ---------------------------------------------------------------------------
// github-protected-patterns
// ---------------------------------------------------------------------------

describe("github-protected-patterns — calls rulesets API", () => {
  test("sends POST to rulesets with release/* pattern", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.git", "");
    const cr = new FakeCommandRunner();
    const ctx = makeCtx({ fileManager: fm, commandRunner: cr });

    const result = await githubProtectedPatternsModule.execute(ctx);

    expect(result.status).toBe("ok");
    expect(result.message).toContain("release/*");

    const call = cr.calls.find((c) => c[0] === "gh" && c[2]?.includes("rulesets"));
    expect(call).toBeDefined();
    expect(call).toContain("POST");
    expect(call?.join(" ")).toContain("release/*");
    expect(call?.join(" ")).toContain("pull_request");
    expect(call?.join(" ")).toContain("non_fast_forward");
    expect(call?.join(" ")).toContain("deletion");
  });

  test("skips when not authenticated", async () => {
    const ctx = makeCtx({
      github: { owner: "testowner", repo: "testrepo", authenticated: false },
    });
    const result = await githubProtectedPatternsModule.execute(ctx);
    expect(result.status).toBe("skipped");
  });

  test("skips when github is undefined", async () => {
    const ctx = makeCtxNoGithub();
    const result = await githubProtectedPatternsModule.execute(ctx);
    expect(result.status).toBe("skipped");
  });

  test("includes workflow job names in required_status_checks", async () => {
    const fm = new FakeFileManager();
    fm.seed("/project/.git", "");
    // Seed at relative path so FakeFileManager.glob matches the pattern,
    // and at absolute path so readText succeeds after join(projectDir, file).
    const workflowContent = `jobs:\n  check:\n    name: "check"\n`;
    fm.seed(".github/workflows/ci.yml", workflowContent);
    fm.seed("/project/.github/workflows/ci.yml", workflowContent);
    const cr = new FakeCommandRunner();
    const ctx = makeCtx({ fileManager: fm, commandRunner: cr });

    await githubProtectedPatternsModule.execute(ctx);

    const call = cr.calls.find((c) => c[0] === "gh" && c[2]?.includes("rulesets"));
    expect(call?.join(" ")).toContain("required_status_checks][0][context]=check");
  });
});
