import { resolve } from "node:path";
import type { CLIResult, FixtureProject, World } from "@questi0nm4rk/feats";
import {
  After,
  composeFixtures,
  createRng,
  Given,
  setupFixture,
} from "@questi0nm4rk/feats";

function isFixtureProject(value: unknown): value is FixtureProject {
  return (
    typeof value === "object" &&
    value !== null &&
    "cleanup" in value &&
    typeof (value as FixtureProject).cleanup === "function"
  );
}

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
    world.project = await composeFixtures([`${String(a)}/bare`, `${String(b)}/bare`], {
      fixtureDir: FIXTURE_DIR,
    });
  }
);

Given<E2EWorld>(
  "a monorepo with {int} random bare languages",
  async (world, count: unknown) => {
    world.binaryPath = resolve(process.cwd(), "dist/ai-guardrails");
    const rng = createRng();
    const langs = rng.sample(ALL_LANGS, Number(count));
    world.project = await composeFixtures(
      langs.map((l) => `${l}/bare`),
      { fixtureDir: FIXTURE_DIR }
    );
  }
);

After(async (world: World) => {
  if ("project" in world && isFixtureProject(world.project)) {
    await world.project.cleanup();
  }
});
