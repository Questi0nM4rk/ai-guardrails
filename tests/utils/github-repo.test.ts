import { describe, expect, test } from "bun:test";
import { detectGitHubRepo } from "@/utils/github-repo";
import { FakeCommandRunner } from "../fakes/fake-command-runner";

const PROJECT_DIR = "/project";

describe("detectGitHubRepo", () => {
  test("detects GitHub SSH remote", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["git", "remote", "get-url", "origin"], {
      stdout: "git@github.com:acme/myrepo\n",
      stderr: "",
      exitCode: 0,
    });
    runner.register(["gh", "auth", "status"], {
      stdout: "Logged in to github.com\n",
      stderr: "",
      exitCode: 0,
    });

    const result = await detectGitHubRepo(runner, PROJECT_DIR);

    expect(result).toEqual({ owner: "acme", repo: "myrepo", authenticated: true });
  });

  test("detects GitHub HTTPS remote", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["git", "remote", "get-url", "origin"], {
      stdout: "https://github.com/acme/myrepo.git\n",
      stderr: "",
      exitCode: 0,
    });
    runner.register(["gh", "auth", "status"], {
      stdout: "Logged in to github.com\n",
      stderr: "",
      exitCode: 0,
    });

    const result = await detectGitHubRepo(runner, PROJECT_DIR);

    expect(result).toEqual({ owner: "acme", repo: "myrepo", authenticated: true });
  });

  test("returns undefined for non-GitHub remote", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["git", "remote", "get-url", "origin"], {
      stdout: "https://gitlab.com/acme/myrepo.git\n",
      stderr: "",
      exitCode: 0,
    });

    const result = await detectGitHubRepo(runner, PROJECT_DIR);

    expect(result).toBeUndefined();
  });

  test("returns undefined when git remote fails", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["git", "remote", "get-url", "origin"], {
      stdout: "",
      stderr: "fatal: No such remote 'origin'\n",
      exitCode: 128,
    });

    const result = await detectGitHubRepo(runner, PROJECT_DIR);

    expect(result).toBeUndefined();
  });

  test("authenticated=false when gh auth fails", async () => {
    const runner = new FakeCommandRunner();
    runner.register(["git", "remote", "get-url", "origin"], {
      stdout: "git@github.com:acme/myrepo\n",
      stderr: "",
      exitCode: 0,
    });
    runner.register(["gh", "auth", "status"], {
      stdout: "",
      stderr: "You are not logged into any GitHub hosts\n",
      exitCode: 1,
    });

    const result = await detectGitHubRepo(runner, PROJECT_DIR);

    expect(result).toEqual({ owner: "acme", repo: "myrepo", authenticated: false });
  });
});
