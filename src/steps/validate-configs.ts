import { join } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import { ALL_GENERATORS } from "@/generators/registry";
import type { ConfigGenerator } from "@/generators/types";
import type { FileManager } from "@/infra/file-manager";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import { computeHash } from "@/utils/hash";

const HASH_HEADER_PATTERN = /^(?:\/\/|#) ai-guardrails:sha256=([0-9a-f]{64})$/;

function hasValidHash(content: string): boolean {
    const firstNewline = content.indexOf("\n");
    if (firstNewline === -1) return false;
    const headerLine = content.slice(0, firstNewline);
    const rest = content.slice(firstNewline + 1);
    const match = HASH_HEADER_PATTERN.exec(headerLine);
    if (!match || !match[1]) return false;
    return computeHash(rest) === match[1];
}

function hasHashHeader(content: string): boolean {
    const firstNewline = content.indexOf("\n");
    if (firstNewline === -1) return false;
    const headerLine = content.slice(0, firstNewline);
    return HASH_HEADER_PATTERN.test(headerLine);
}

async function validateOne(
    generator: ConfigGenerator,
    projectDir: string,
    fileManager: FileManager,
    config: ResolvedConfig | null
): Promise<string | null> {
    let content: string;
    try {
        content = await fileManager.readText(join(projectDir, generator.configFile));
    } catch {
        return `missing: ${generator.configFile}`;
    }

    if (!content.trim()) return `empty: ${generator.configFile}`;

    // Tamper check: verify hash header matches body.
    if (hasHashHeader(content) && !hasValidHash(content)) {
        return `tampered: ${generator.configFile}`;
    }

    // Staleness check (--check mode): regenerate and compare against on-disk content.
    // Generators that require extra context (e.g. lefthook needs active plugins) throw —
    // those fall back to tamper-only detection.
    if (config !== null) {
        let expected: string | null = null;
        try {
            expected = generator.generate(config);
        } catch {
            // Generator cannot run with config alone — skip staleness check.
        }
        if (expected !== null && expected !== content) {
            return `stale: ${generator.configFile}`;
        }
    }

    return null;
}

export async function validateConfigsStep(
    projectDir: string,
    fileManager: FileManager,
    config: ResolvedConfig | null = null
): Promise<StepResult> {
    const problems = (
        await Promise.all(
            ALL_GENERATORS.map((g) => validateOne(g, projectDir, fileManager, config))
        )
    ).filter((p): p is string => p !== null);

    if (problems.length > 0) {
        return error(`Config validation failed: ${problems.join(", ")}`);
    }

    return ok(`All ${ALL_GENERATORS.length} config files validated`);
}
