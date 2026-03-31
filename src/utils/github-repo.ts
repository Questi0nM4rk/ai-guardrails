import type { CommandRunner } from "@/infra/command-runner";

export interface GitHubRepoInfo {
  readonly owner: string;
  readonly repo: string;
  readonly authenticated: boolean;
}

const SSH_PATTERN = /git@github\.com:([^/]+)\/([^/.]+)/;
const HTTPS_PATTERN = /github\.com\/([^/]+)\/([^/.]+)/;

/** Detect GitHub repo from git remote and gh auth status. */
export async function detectGitHubRepo(
  commandRunner: CommandRunner,
  projectDir: string
): Promise<GitHubRepoInfo | undefined> {
  const remoteResult = await commandRunner.run(["git", "remote", "get-url", "origin"], {
    cwd: projectDir,
  });
  if (remoteResult.exitCode !== 0) return undefined;

  const url = remoteResult.stdout.trim();
  const match = SSH_PATTERN.exec(url) ?? HTTPS_PATTERN.exec(url);
  if (match === null) return undefined;

  const owner = match[1];
  const repo = match[2];
  if (owner === undefined || repo === undefined) return undefined;

  const authResult = await commandRunner.run(["gh", "auth", "status"], {
    cwd: projectDir,
  });
  const authenticated = authResult.exitCode === 0;

  return { owner, repo, authenticated };
}
