import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then } from "@questi0nm4rk/feats";
import {
  buildResolvedConfig,
  MachineConfigSchema,
  ProjectConfigSchema,
} from "@/config/schema";
import { claudeSettingsGenerator } from "@/generators/claude-settings";

interface HookBinaryResolutionWorld extends World {
  settingsJson: string;
  hookCommands: string[];
}

interface HookEntry {
  type: string;
  command: string;
}

interface PreToolUseEntry {
  matcher: string;
  hooks: HookEntry[];
}

interface ParsedSettings {
  hooks?: {
    PreToolUse?: PreToolUseEntry[];
  };
}

function makeDefaultConfig() {
  return buildResolvedConfig(
    MachineConfigSchema.parse({}),
    ProjectConfigSchema.parse({})
  );
}

function extractHookCommands(settingsJson: string): string[] {
  const parsed = JSON.parse(settingsJson) as ParsedSettings;
  const preToolUse = parsed.hooks?.PreToolUse ?? [];
  return preToolUse.flatMap((entry) => entry.hooks.map((h) => h.command));
}

Given<HookBinaryResolutionWorld>(
  "generated claude settings",
  (world: HookBinaryResolutionWorld) => {
    world.settingsJson = claudeSettingsGenerator.generate(makeDefaultConfig());
    world.hookCommands = extractHookCommands(world.settingsJson);
  }
);

Then<HookBinaryResolutionWorld>(
  "all hook commands should contain {string}",
  (world: HookBinaryResolutionWorld, text: unknown) => {
    expect(world.hookCommands.length).toBeGreaterThan(0);
    for (const cmd of world.hookCommands) {
      expect(cmd).toContain(String(text));
    }
  }
);

Then<HookBinaryResolutionWorld>(
  "no hook command should contain {string}",
  (world: HookBinaryResolutionWorld, text: unknown) => {
    for (const cmd of world.hookCommands) {
      expect(cmd).not.toContain(String(text));
    }
  }
);

Then<HookBinaryResolutionWorld>(
  "hook commands should use {string} not {string}",
  (world: HookBinaryResolutionWorld, preferred: unknown, disallowed: unknown) => {
    expect(world.hookCommands.length).toBeGreaterThan(0);
    for (const cmd of world.hookCommands) {
      expect(cmd).toContain(String(preferred));
      expect(cmd).not.toContain(String(disallowed));
    }
  }
);
