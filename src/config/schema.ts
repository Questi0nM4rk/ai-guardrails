import { minimatch } from "minimatch";
import { z } from "zod";

const ConfigStrategySchema = z.enum(["merge", "replace", "skip"]);
export type ConfigStrategy = z.infer<typeof ConfigStrategySchema>;
export { ConfigStrategySchema };

const IgnoreEntrySchema = z.object({
  rule: z.string().regex(/^[\w-]+\/[\w\-.]+$/, "Format: linter/RULE_CODE"),
  reason: z.string().min(1, "Reason is required"),
});

const MachineConfigSchema = z.object({
  profile: z.enum(["strict", "standard", "minimal"]).default("standard"),
  ignore: z.array(IgnoreEntrySchema).default([]),
});

export type Profile = "strict" | "standard" | "minimal";
export const PROFILES = [
  "strict",
  "standard",
  "minimal",
] as const satisfies readonly Profile[];

export type MachineConfig = z.infer<typeof MachineConfigSchema>;

export { MachineConfigSchema };

const ConfigValuesSchema = z
  .object({
    line_length: z.number().int().min(60).max(200).default(88),
    indent_width: z
      .number()
      .int()
      .refine((v) => v === 2 || v === 4, {
        message: "indent_width must be 2 or 4",
      })
      .default(2),
    python_version: z
      .string()
      .regex(/^\d+\.\d+$/)
      .optional(),
  })
  .passthrough();

const AllowEntrySchema = z.object({
  rule: z.string().regex(/^[\w-]+\/[\w\-.]+$/),
  glob: z.string().min(1),
  reason: z.string().min(1),
});

const HooksConfigSchema = z.object({
  managed_files: z.array(z.string()).optional(),
  managed_paths: z.array(z.string()).optional(),
  protected_read_paths: z.array(z.string()).optional(),
  disabled_groups: z.array(z.string()).optional(),
});

export type HooksSchemaConfig = z.infer<typeof HooksConfigSchema>;

const ProjectConfigSchema = z.object({
  profile: z.enum(["strict", "standard", "minimal"]).optional(),
  config: ConfigValuesSchema.default({}),
  ignore: z.array(IgnoreEntrySchema).default([]),
  allow: z.array(AllowEntrySchema).default([]),
  hooks: HooksConfigSchema.optional(),
});

export type ProjectConfig = z.infer<typeof ProjectConfigSchema>;

export { ProjectConfigSchema };

export interface ResolvedConfig {
  profile: "strict" | "standard" | "minimal";
  ignore: ReadonlyArray<{ rule: string; reason: string }>;
  allow: ReadonlyArray<{ rule: string; glob: string; reason: string }>;
  values: {
    line_length: number;
    indent_width: number;
    python_version?: string;
    [key: string]: unknown;
  };
  hooks?: HooksSchemaConfig;
  ignoredRules: ReadonlySet<string>;
  isAllowed(rule: string, filePath: string): boolean;
}

export function buildResolvedConfig(
  machine: MachineConfig,
  project: ProjectConfig
): ResolvedConfig {
  const profile = project.profile ?? machine.profile;

  // Merge ignores: machine → project, deduped by rule
  const ignoreMap = new Map<string, string>();
  for (const entry of [...machine.ignore, ...project.ignore]) {
    ignoreMap.set(entry.rule, entry.reason);
  }
  const ignore = Array.from(ignoreMap.entries()).map(([rule, reason]) => ({
    rule,
    reason,
  }));
  const ignoredRules = new Set(ignore.map((e) => e.rule));
  const allow = project.allow;
  const { line_length, indent_width, python_version, ...passthroughRest } =
    project.config;
  const values: ResolvedConfig["values"] = {
    ...passthroughRest,
    line_length,
    indent_width,
    ...(python_version !== undefined && { python_version }),
  };

  return {
    profile,
    ignore,
    allow,
    values,
    ...(project.hooks !== undefined && { hooks: project.hooks }),
    ignoredRules,
    isAllowed(rule: string, filePath: string): boolean {
      if (ignoredRules.has(rule)) return true;
      return allow.some(
        (entry) => entry.rule === rule && minimatch(filePath, entry.glob)
      );
    },
  };
}
