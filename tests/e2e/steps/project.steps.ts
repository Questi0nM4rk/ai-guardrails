import { resolve } from "node:path";
import type { CLIResult, FixtureProject, World } from "@questi0nm4rk/feats";
import {
  After,
  composeFixtures,
  createRng,
  Given,
  setupFixture,
} from "@questi0nm4rk/feats";

const FIXTURE_DIR = resolve(import.meta.dir, "../fixtures");

const ALL_LANGS = [
  "typescript",
  "python",
  "rust",
  "go",
  "shell",
  "cpp",
  "lua",
] as const;

export interface E2EWorld extends World {
  project: FixtureProject;
  result: CLIResult;
  binaryPath: string;
}

Given<E2EWorld>("a bare {string} fixture project", async (world, lang: unknown) => {
  world.binaryPath = resolve(process.cwd(), "dist/ai-guardrails");
  // Fixture dirs are nested: fixtures/<lang>/bare/
  // setupFixture needs the subpath for copy but uses it for temp dir naming.
  // The fixtureDir points to the specific bare dir.
  world.project = await setupFixture("bare", {
    fixtureDir: resolve(FIXTURE_DIR, String(lang)),
  });
});

Given<E2EWorld>(
  "a preconfigured {string} fixture project",
  async (world, lang: unknown) => {
    world.binaryPath = resolve(process.cwd(), "dist/ai-guardrails");
    world.project = await setupFixture("preconfigured", {
      fixtureDir: resolve(FIXTURE_DIR, String(lang)),
    });
  }
);

Given<E2EWorld>(
  "a monorepo combining bare {string} and bare {string}",
  async (world, a: unknown, b: unknown) => {
    world.binaryPath = resolve(process.cwd(), "dist/ai-guardrails");
    world.project = await composeFixtures(
      [
        resolve(FIXTURE_DIR, String(a), "bare"),
        resolve(FIXTURE_DIR, String(b), "bare"),
      ],
      { fixtureDir: "/" }
    );
  }
);

Given<E2EWorld>(
  "a monorepo with {int} random bare languages",
  async (world, count: unknown) => {
    world.binaryPath = resolve(process.cwd(), "dist/ai-guardrails");
    const rng = createRng();
    const langs = rng.sample(ALL_LANGS, Number(count));
    world.project = await composeFixtures(
      langs.map((l) => resolve(FIXTURE_DIR, l, "bare")),
      { fixtureDir: "/" }
    );
  }
);

After(async (world: World) => {
  if ("project" in world && world.project !== undefined) {
    const project = world.project;
    if (typeof project === "object" && project !== null && "cleanup" in project) {
      await (project as FixtureProject).cleanup();
    }
  }
});
