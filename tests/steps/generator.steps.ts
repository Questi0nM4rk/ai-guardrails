import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import type { ResolvedConfig } from "@/config/schema";
import type { DetectedAgentTools } from "@/generators/agent-rules";
import {
  AGENT_SYMLINKS,
  agentRulesGenerator,
  buildAgentRules,
  detectAgentTools,
} from "@/generators/agent-rules";

const AGENT_TOOL_KEYS = [
  "claude",
  "cursor",
  "windsurf",
  "copilot",
  "cline",
  "aider",
] as const satisfies readonly (keyof DetectedAgentTools)[];

function toAgentToolKey(value: string): keyof DetectedAgentTools {
  const found = AGENT_TOOL_KEYS.find((k) => k === value);
  if (found !== undefined) {
    return found;
  }
  throw new Error(
    `Invalid agent tool key: "${value}". Expected one of: ${AGENT_TOOL_KEYS.join(", ")}`
  );
}

import { biomeGenerator } from "@/generators/biome";
import { claudeSettingsGenerator } from "@/generators/claude-settings";
import { generateLefthookConfig, lefthookGenerator } from "@/generators/lefthook";
import { ruffGenerator } from "@/generators/ruff";
import type { ConfigGenerator } from "@/generators/types";
import type { LanguagePlugin } from "@/languages/types";
import { HASH_PREFIX, makeHashHeader } from "@/utils/hash";
import { FakeFileManager } from "../fakes/fake-file-manager";

interface GeneratorWorld extends World {
  generator: ConfigGenerator;
  generatorOutput: string;
  detectedTools: DetectedAgentTools;
  agentRules: string;
  fm: FakeFileManager;
  projectDir: string;
  thrownError: unknown;
}

const PROJECT_DIR = "/project";

// ─── Default config factory ───────────────────────────────────────────────────

function makeDefaultConfig(overrides?: Partial<ResolvedConfig>): ResolvedConfig {
  return {
    profile: "standard",
    ignore: [],
    allow: [],
    values: { line_length: 88, indent_width: 2 },
    ignoredRules: new Set(),
    ignorePaths: [],
    noConsoleLevel: "warn" as const,
    isAllowed: () => false,
    ...overrides,
  };
}

function makePlugin(id: string): LanguagePlugin {
  return {
    id,
    name: id,
    detect: async () => true,
    runners: () => [],
  };
}

// ─── Generator Given steps ────────────────────────────────────────────────────

Given<GeneratorWorld>("the biome generator", (world: GeneratorWorld) => {
  world.generator = biomeGenerator;
});

Given<GeneratorWorld>("the ruff generator", (world: GeneratorWorld) => {
  world.generator = ruffGenerator;
});

Given<GeneratorWorld>("the lefthook generator", (world: GeneratorWorld) => {
  world.generator = lefthookGenerator;
});

Given<GeneratorWorld>("the claude-settings generator", (world: GeneratorWorld) => {
  world.generator = claudeSettingsGenerator;
});

Given<GeneratorWorld>("the agent-rules generator", (world: GeneratorWorld) => {
  world.generator = agentRulesGenerator;
});

// ─── Project detection Given steps ────────────────────────────────────────────

Given<GeneratorWorld>(
  "a project with file {string}",
  (world: GeneratorWorld, file: unknown) => {
    world.fm = new FakeFileManager();
    world.projectDir = PROJECT_DIR;
    world.fm.seed(`${PROJECT_DIR}/${String(file)}`, "# content");
  }
);

Given<GeneratorWorld>("an empty project", (world: GeneratorWorld) => {
  world.fm = new FakeFileManager();
  world.projectDir = PROJECT_DIR;
});

// ─── When ─────────────────────────────────────────────────────────────────────

When<GeneratorWorld>("I generate with default config", (world: GeneratorWorld) => {
  world.generatorOutput = world.generator.generate(makeDefaultConfig());
});

When<GeneratorWorld>(
  "I generate with profile {string}",
  (world: GeneratorWorld, profile: unknown) => {
    const p = String(profile);
    if (p !== "strict" && p !== "standard" && p !== "minimal") {
      throw new Error(`Unknown profile: "${p}". Expected: strict, standard, minimal`);
    }
    world.generatorOutput = world.generator.generate(makeDefaultConfig({ profile: p }));
  }
);

When<GeneratorWorld>(
  "I generate with line_length {int}",
  (world: GeneratorWorld, lineLength: unknown) => {
    world.generatorOutput = world.generator.generate(
      makeDefaultConfig({
        values: { line_length: Number(lineLength), indent_width: 2 },
      })
    );
  }
);

When<GeneratorWorld>(
  "I generate with indent_width {int}",
  (world: GeneratorWorld, indentWidth: unknown) => {
    world.generatorOutput = world.generator.generate(
      makeDefaultConfig({
        values: { line_length: 88, indent_width: Number(indentWidth) },
      })
    );
  }
);

When<GeneratorWorld>(
  "I generate with biome_version {string}",
  (world: GeneratorWorld, version: unknown) => {
    world.generatorOutput = world.generator.generate(
      makeDefaultConfig({
        values: { line_length: 88, indent_width: 2, biome_version: String(version) },
      })
    );
  }
);

When<GeneratorWorld>(
  "I generate with ignorePaths containing {string}",
  (world: GeneratorWorld, path: unknown) => {
    world.generatorOutput = world.generator.generate(
      makeDefaultConfig({ ignorePaths: [String(path)] })
    );
  }
);

When<GeneratorWorld>(
  "I generate with ignorePaths {string} and {string}",
  (world: GeneratorWorld, p1: unknown, p2: unknown) => {
    world.generatorOutput = world.generator.generate(
      makeDefaultConfig({ ignorePaths: [String(p1), String(p2)] })
    );
  }
);

When<GeneratorWorld>(
  "I call generate directly on the lefthook generator",
  (world: GeneratorWorld) => {
    try {
      world.generatorOutput = lefthookGenerator.generate(makeDefaultConfig());
    } catch (e: unknown) {
      world.thrownError = e;
    }
  }
);

When<GeneratorWorld>(
  "I generate lefthook config with no plugins",
  (world: GeneratorWorld) => {
    world.generatorOutput = generateLefthookConfig(makeDefaultConfig(), []);
  }
);

When<GeneratorWorld>(
  "I generate lefthook config with typescript plugin and no ignorePaths",
  (world: GeneratorWorld) => {
    world.generatorOutput = generateLefthookConfig(makeDefaultConfig(), [
      makePlugin("typescript"),
    ]);
  }
);

When<GeneratorWorld>(
  "I generate lefthook config with typescript plugin and ignorePaths {string}",
  (world: GeneratorWorld, path: unknown) => {
    world.generatorOutput = generateLefthookConfig(
      makeDefaultConfig({ ignorePaths: [String(path)] }),
      [makePlugin("typescript")]
    );
  }
);

When<GeneratorWorld>(
  "I generate lefthook config with no plugins and ignorePaths {string}",
  (world: GeneratorWorld, path: unknown) => {
    world.generatorOutput = generateLefthookConfig(
      makeDefaultConfig({ ignorePaths: [String(path)] }),
      []
    );
  }
);

When<GeneratorWorld>(
  "I generate lefthook config with python plugin",
  (world: GeneratorWorld) => {
    world.generatorOutput = generateLefthookConfig(makeDefaultConfig(), [
      makePlugin("python"),
    ]);
  }
);

When<GeneratorWorld>(
  "I generate lefthook config with typescript plugin",
  (world: GeneratorWorld) => {
    world.generatorOutput = generateLefthookConfig(makeDefaultConfig(), [
      makePlugin("typescript"),
    ]);
  }
);

When<GeneratorWorld>(
  "I generate lefthook config with python and typescript plugins",
  (world: GeneratorWorld) => {
    world.generatorOutput = generateLefthookConfig(makeDefaultConfig(), [
      makePlugin("python"),
      makePlugin("typescript"),
    ]);
  }
);

When<GeneratorWorld>("I detect agent tools", async (world: GeneratorWorld) => {
  world.detectedTools = await detectAgentTools(
    world.projectDir ?? PROJECT_DIR,
    world.fm ?? new FakeFileManager()
  );
});

When<GeneratorWorld>(
  "I build agent rules for {string}",
  (world: GeneratorWorld, tool: unknown) => {
    world.agentRules = buildAgentRules(toAgentToolKey(String(tool)));
  }
);

// ─── Generator id / configFile ────────────────────────────────────────────────

Then<GeneratorWorld>(
  "the generator id should be {string}",
  (world: GeneratorWorld, id: unknown) => {
    expect(world.generator.id).toBe(String(id));
  }
);

Then<GeneratorWorld>(
  "the generator configFile should be {string}",
  (world: GeneratorWorld, file: unknown) => {
    expect(world.generator.configFile).toBe(String(file));
  }
);

// ─── Output content assertions ─────────────────────────────────────────────────

Then<GeneratorWorld>(
  "the output should match the snapshot",
  (world: GeneratorWorld) => {
    expect(world.generatorOutput).toMatchSnapshot();
  }
);

Then<GeneratorWorld>(
  "the output should contain {string}",
  (world: GeneratorWorld, text: unknown) => {
    expect(world.generatorOutput).toContain(String(text));
  }
);

Then<GeneratorWorld>(
  "the output should not contain {string}",
  (world: GeneratorWorld, text: unknown) => {
    expect(world.generatorOutput).not.toContain(String(text));
  }
);

Then<GeneratorWorld>(
  "the output should start with a JSONC hash header",
  (world: GeneratorWorld) => {
    expect(world.generatorOutput).toMatch(/^\/\/ ai-guardrails:sha256=[0-9a-f]{64}\n/);
  }
);

Then<GeneratorWorld>(
  "the output should have a valid TOML hash header",
  (world: GeneratorWorld) => {
    const newlineIdx = world.generatorOutput.indexOf("\n");
    const headerLine = world.generatorOutput.slice(0, newlineIdx);
    const body = world.generatorOutput.slice(newlineIdx + 1);
    expect(headerLine).toStartWith(HASH_PREFIX);
    expect(headerLine).toBe(makeHashHeader(body));
  }
);

Then<GeneratorWorld>("the output should be valid JSON", (world: GeneratorWorld) => {
  expect(() => JSON.parse(world.generatorOutput)).not.toThrow();
});

Then<GeneratorWorld>(
  "the output should start with {string}",
  (world: GeneratorWorld, prefix: unknown) => {
    expect(world.generatorOutput.startsWith(String(prefix))).toBe(true);
  }
);

Then<GeneratorWorld>(
  "the permissions.deny array should be non-empty",
  (world: GeneratorWorld) => {
    const parsed = JSON.parse(world.generatorOutput) as {
      permissions?: { deny?: unknown[] };
    };
    expect(Array.isArray(parsed.permissions?.deny)).toBe(true);
    expect((parsed.permissions?.deny ?? []).length).toBeGreaterThan(0);
  }
);

Then<GeneratorWorld>(
  "it should throw {string}",
  (world: GeneratorWorld, message: unknown) => {
    expect(world.thrownError).toBeDefined();
    if (world.thrownError instanceof Error) {
      expect(world.thrownError.message).toContain(String(message));
    }
  }
);

Then<GeneratorWorld>(
  "the output should match the main-or-master OR pattern",
  (world: GeneratorWorld) => {
    expect(world.generatorOutput).toMatch(
      /"\$branch"\s*=\s*"main"\s*\]\s*\|\|\s*\[.*"\$branch"\s*=\s*"master"/
    );
  }
);

Then<GeneratorWorld>(
  "the biome-fix section should not contain {string}",
  (world: GeneratorWorld, text: unknown) => {
    const biomeFix =
      world.generatorOutput.match(/biome-fix:([\s\S]*?)(?:\n {4}\w|\ncommit)/)?.[1] ??
      "";
    expect(biomeFix).not.toContain(String(text));
  }
);

Then<GeneratorWorld>(
  "the biome-fix section should contain {string}",
  (world: GeneratorWorld, text: unknown) => {
    const biomeFix =
      world.generatorOutput.match(/biome-fix:([\s\S]*?)(?:\n {4}\w|\ncommit)/)?.[1] ??
      "";
    expect(biomeFix).toContain(String(text));
  }
);

Then<GeneratorWorld>(
  "the codespell section should contain {string}",
  (world: GeneratorWorld, text: unknown) => {
    const codespell =
      world.generatorOutput.match(/codespell:([\s\S]*?)(?:\n {4}\w|\ncommit)/)?.[1] ??
      "";
    expect(codespell).toContain(String(text));
  }
);

// ─── Agent tool detection ──────────────────────────────────────────────────────

Then<GeneratorWorld>("claude should be detected", (world: GeneratorWorld) => {
  expect(world.detectedTools.claude).toBe(true);
});

Then<GeneratorWorld>("cursor should be detected", (world: GeneratorWorld) => {
  expect(world.detectedTools.cursor).toBe(true);
});

Then<GeneratorWorld>("windsurf should be detected", (world: GeneratorWorld) => {
  expect(world.detectedTools.windsurf).toBe(true);
});

Then<GeneratorWorld>("copilot should be detected", (world: GeneratorWorld) => {
  expect(world.detectedTools.copilot).toBe(true);
});

Then<GeneratorWorld>("cline should be detected", (world: GeneratorWorld) => {
  expect(world.detectedTools.cline).toBe(true);
});

Then<GeneratorWorld>("aider should be detected", (world: GeneratorWorld) => {
  expect(world.detectedTools.aider).toBe(true);
});

Then<GeneratorWorld>("no agent tools should be detected", (world: GeneratorWorld) => {
  expect(world.detectedTools.claude).toBe(false);
  expect(world.detectedTools.cursor).toBe(false);
  expect(world.detectedTools.windsurf).toBe(false);
  expect(world.detectedTools.copilot).toBe(false);
  expect(world.detectedTools.cline).toBe(false);
  expect(world.detectedTools.aider).toBe(false);
});

// ─── buildAgentRules assertions ────────────────────────────────────────────────

Then<GeneratorWorld>(
  "the rules should contain {string}",
  (world: GeneratorWorld, text: unknown) => {
    expect(world.agentRules).toContain(String(text));
  }
);

// ─── AGENT_SYMLINKS assertions ─────────────────────────────────────────────────

Then<GeneratorWorld>(
  "AGENT_SYMLINKS cursor should be {string}",
  (_world: GeneratorWorld, value: unknown) => {
    expect(AGENT_SYMLINKS.cursor).toBe(String(value));
  }
);

Then<GeneratorWorld>(
  "AGENT_SYMLINKS windsurf should be {string}",
  (_world: GeneratorWorld, value: unknown) => {
    expect(AGENT_SYMLINKS.windsurf).toBe(String(value));
  }
);
