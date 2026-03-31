import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { githubBranchProtectionModule } from "@/init/modules/github-branch-protection";
import { githubCcReviewerModule } from "@/init/modules/github-cc-reviewer";
import { githubPrTemplateModule } from "@/init/modules/github-pr-template";
import { githubProtectedPatternsModule } from "@/init/modules/github-protected-patterns";
import type { InitContext, InitModuleResult } from "@/init/types";
import { FakeCommandRunner } from "../fakes/fake-command-runner";
import { FakeConsole } from "../fakes/fake-console";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";

interface GithubModulesWorld extends World {
  ctx: InitContext;
  result: InitModuleResult;
  fm: FakeFileManager;
  cr: FakeCommandRunner;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function freshConfig() {
  return buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse({})
  );
}

function makeCtx(overrides?: Partial<InitContext>): InitContext {
  const fm = new FakeFileManager();
  fm.seed(`${PROJECT_DIR}/.git`, "");
  return {
    projectDir: PROJECT_DIR,
    fileManager: fm,
    commandRunner: new FakeCommandRunner(),
    console: new FakeConsole(),
    config: freshConfig(),
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

/** Returns a ctx without the optional `github` field (exactOptionalPropertyTypes-safe). */
function makeCtxNoGithub(
  overrides?: Omit<Partial<InitContext>, "github">
): InitContext {
  const { github: _github, ...base } = makeCtx(overrides);
  return base;
}

// ── Given steps ──────────────────────────────────────────────────────────────

Given<GithubModulesWorld>(
  "a GitHub project for PR template testing",
  (world: GithubModulesWorld) => {
    world.fm = new FakeFileManager();
    world.cr = new FakeCommandRunner();
    world.fm.seed(`${PROJECT_DIR}/.git`, "");
    world.ctx = makeCtx({ fileManager: world.fm, commandRunner: world.cr });
  }
);

Given<GithubModulesWorld>(
  "a GitHub project with existing PR template",
  (world: GithubModulesWorld) => {
    world.fm = new FakeFileManager();
    world.cr = new FakeCommandRunner();
    world.fm.seed(`${PROJECT_DIR}/.git`, "");
    world.fm.seed(`${PROJECT_DIR}/.github/pull_request_template.md`, "# existing");
    world.ctx = makeCtx({ fileManager: world.fm, commandRunner: world.cr });
  }
);

Given<GithubModulesWorld>(
  "a GitHub project with authentication",
  (world: GithubModulesWorld) => {
    world.fm = new FakeFileManager();
    world.cr = new FakeCommandRunner();
    world.fm.seed(`${PROJECT_DIR}/.git`, "");
    world.ctx = makeCtx({ fileManager: world.fm, commandRunner: world.cr });
  }
);

Given<GithubModulesWorld>(
  "a GitHub project with existing .coderabbit.yaml",
  (world: GithubModulesWorld) => {
    world.fm = new FakeFileManager();
    world.cr = new FakeCommandRunner();
    world.fm.seed(`${PROJECT_DIR}/.git`, "");
    world.fm.seed(`${PROJECT_DIR}/.coderabbit.yaml`, "# existing");
    world.ctx = makeCtx({ fileManager: world.fm, commandRunner: world.cr });
  }
);

Given<GithubModulesWorld>(
  "a GitHub project without authentication",
  (world: GithubModulesWorld) => {
    world.fm = new FakeFileManager();
    world.cr = new FakeCommandRunner();
    world.fm.seed(`${PROJECT_DIR}/.git`, "");
    world.ctx = makeCtxNoGithub({ fileManager: world.fm, commandRunner: world.cr });
  }
);

Given<GithubModulesWorld>(
  "a GitHub project with authentication and workflows",
  (world: GithubModulesWorld) => {
    world.fm = new FakeFileManager();
    world.cr = new FakeCommandRunner();
    world.fm.seed(`${PROJECT_DIR}/.git`, "");
    world.ctx = makeCtx({ fileManager: world.fm, commandRunner: world.cr });
  }
);

Given<GithubModulesWorld>(
  "a GitHub project with authentication and a workflow named {string}",
  (world: GithubModulesWorld, jobName: unknown) => {
    const name = String(jobName);
    world.fm = new FakeFileManager();
    world.cr = new FakeCommandRunner();
    world.fm.seed(`${PROJECT_DIR}/.git`, "");
    const workflowContent = `jobs:\n  ci:\n    name: "${name}"\n`;
    world.fm.seed(`${PROJECT_DIR}/.github/workflows/ci.yml`, workflowContent);
    world.ctx = makeCtx({ fileManager: world.fm, commandRunner: world.cr });
  }
);

Given<GithubModulesWorld>(
  "a GitHub project with authentication and branch protection",
  (world: GithubModulesWorld) => {
    world.fm = new FakeFileManager();
    world.cr = new FakeCommandRunner();
    world.fm.seed(`${PROJECT_DIR}/.git`, "");
    world.ctx = makeCtx({ fileManager: world.fm, commandRunner: world.cr });
  }
);

// ── When steps ───────────────────────────────────────────────────────────────

When<GithubModulesWorld>(
  "the github-pr-template module executes",
  async (world: GithubModulesWorld) => {
    world.result = await githubPrTemplateModule.execute(world.ctx);
  }
);

When<GithubModulesWorld>(
  "the github-cc-reviewer module executes",
  async (world: GithubModulesWorld) => {
    world.result = await githubCcReviewerModule.execute(world.ctx);
  }
);

When<GithubModulesWorld>(
  "the github-branch-protection module executes",
  async (world: GithubModulesWorld) => {
    world.result = await githubBranchProtectionModule.execute(world.ctx);
  }
);

When<GithubModulesWorld>(
  "the github-protected-patterns module executes",
  async (world: GithubModulesWorld) => {
    world.result = await githubProtectedPatternsModule.execute(world.ctx);
  }
);

// ── Then steps ────────────────────────────────────────────────────────────────

Then<GithubModulesWorld>(
  "the module should return status {string}",
  (world: GithubModulesWorld, status: unknown) => {
    const s = String(status);
    expect(["ok", "skipped", "error"]).toContain(s);
    const expected = s as "ok" | "skipped" | "error";
    expect(world.result.status).toBe(expected);
  }
);

Then<GithubModulesWorld>(
  "the github module should write {string}",
  (world: GithubModulesWorld, relativePath: unknown) => {
    const suffix = String(relativePath);
    const written = world.fm.written.map(([p]) => p);
    expect(written.some((p) => p.endsWith(suffix))).toBe(true);
  }
);

Then<GithubModulesWorld>(
  "the template should contain {string}",
  (world: GithubModulesWorld, text: unknown) => {
    const entry = world.fm.written.find(([p]) =>
      p.endsWith("pull_request_template.md")
    );
    expect(entry).toBeDefined();
    const content = entry?.[1] ?? "";
    expect(content).toContain(String(text));
  }
);

Then<GithubModulesWorld>(
  "the config should contain {string}",
  (world: GithubModulesWorld, text: unknown) => {
    const entry = world.fm.written.find(([p]) => p.endsWith(".coderabbit.yaml"));
    expect(entry).toBeDefined();
    const content = entry?.[1] ?? "";
    expect(content).toContain(String(text));
  }
);

Then<GithubModulesWorld>(
  "gh api should be called with {string}",
  (world: GithubModulesWorld, urlFragment: unknown) => {
    const fragment = String(urlFragment);
    const match = world.cr.calls.find(
      (c) => c[0] === "gh" && c.some((arg) => arg.includes(fragment))
    );
    expect(match).toBeDefined();
  }
);

Then<GithubModulesWorld>(
  "the call should include {string}",
  (world: GithubModulesWorld, text: unknown) => {
    const fragment = String(text);
    const match = world.cr.calls.find(
      (c) => c[0] === "gh" && c.join(" ").includes(fragment)
    );
    expect(match).toBeDefined();
  }
);

Then<GithubModulesWorld>(
  "the call should include {string} in required status checks",
  (world: GithubModulesWorld, jobName: unknown) => {
    const name = String(jobName);
    const match = world.cr.calls.find(
      (c) =>
        c[0] === "gh" &&
        c.some((arg) => arg.includes("branches/main/protection")) &&
        c.join(" ").includes(name)
    );
    expect(match).toBeDefined();
  }
);
