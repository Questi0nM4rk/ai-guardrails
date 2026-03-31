import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import { setupAgentInstructionsStep } from "@/steps/setup-agent-instructions";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";
const ORIGINAL_CONTENT = "# My Existing Project\n\nExisting documentation.\n";

interface AgentInstructionsWorld extends World {
  fm: FakeFileManager;
}

Given<AgentInstructionsWorld>(
  "a project for agent instructions testing",
  (world: AgentInstructionsWorld) => {
    world.fm = new FakeFileManager();
  }
);

Given<AgentInstructionsWorld>(
  "a project without CLAUDE.md",
  (world: AgentInstructionsWorld) => {
    world.fm = new FakeFileManager();
  }
);

Given<AgentInstructionsWorld>(
  "a project with existing CLAUDE.md",
  (world: AgentInstructionsWorld) => {
    world.fm = new FakeFileManager();
    world.fm.seed(`${PROJECT_DIR}/CLAUDE.md`, ORIGINAL_CONTENT);
  }
);

Given<AgentInstructionsWorld>(
  "a project with CLAUDE.md containing {string}",
  (world: AgentInstructionsWorld, text: unknown) => {
    world.fm = new FakeFileManager();
    world.fm.seed(
      `${PROJECT_DIR}/CLAUDE.md`,
      `# My Project\n\n## ${String(text)} - Code Standards\n\nAlready present.\n`
    );
  }
);

When<AgentInstructionsWorld>(
  "agent instructions step runs",
  async (world: AgentInstructionsWorld) => {
    await setupAgentInstructionsStep(PROJECT_DIR, world.fm);
  }
);

Then<AgentInstructionsWorld>(
  "the agent file {string} should be written",
  (world: AgentInstructionsWorld, filename: unknown) => {
    const name = String(filename);
    const writtenPaths = world.fm.written.map(([p]) => p);
    expect(writtenPaths.some((p) => p.endsWith(name))).toBe(true);
  }
);

Then<AgentInstructionsWorld>(
  "the agent file {string} should contain {string}",
  async (world: AgentInstructionsWorld, filename: unknown, text: unknown) => {
    const name = String(filename);
    const searchText = String(text);
    // Prefer the final written content — check the in-memory file state
    const content = await findFileContent(world.fm, PROJECT_DIR, name);
    expect(content).toContain(searchText);
  }
);

Then<AgentInstructionsWorld>(
  "{string} should contain the original content",
  async (world: AgentInstructionsWorld, filename: unknown) => {
    const name = String(filename);
    const content = await findFileContent(world.fm, PROJECT_DIR, name);
    expect(content).toContain(ORIGINAL_CONTENT.trim());
  }
);

Then<AgentInstructionsWorld>(
  "{string} should contain exactly one {string} section",
  async (world: AgentInstructionsWorld, filename: unknown, sectionText: unknown) => {
    const name = String(filename);
    const search = String(sectionText);
    const content = await findFileContent(world.fm, PROJECT_DIR, name);
    // Count non-overlapping occurrences
    const count = content.split(search).length - 1;
    expect(count).toBe(1);
  }
);

/** Read the current in-memory content for a file by suffix match. */
async function findFileContent(
  fm: FakeFileManager,
  projectDir: string,
  filename: string
): Promise<string> {
  try {
    return await fm.readText(`${projectDir}/${filename}`);
  } catch {
    // Try to find by written array if the path isn't seeded but was written
    const entry = fm.written.find(([p]) => p.endsWith(filename));
    if (entry !== undefined) return entry[1];
    throw new Error(`File not found in fake: ${filename}`);
  }
}
