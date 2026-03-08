import { join } from "node:path";
import { ALL_GENERATORS } from "@/generators/registry";
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
    dest: string,
    configFile: string,
    fileManager: FileManager
): Promise<string | null> {
    try {
        const content = await fileManager.readText(dest);
        if (!content.trim()) return `empty: ${configFile}`;
        if (hasHashHeader(content) && !hasValidHash(content)) {
            return `tampered: ${configFile}`;
        }
        return null;
    } catch {
        return `missing: ${configFile}`;
    }
}

export async function validateConfigsStep(
    projectDir: string,
    fileManager: FileManager
): Promise<StepResult> {
    const problems = (
        await Promise.all(
            ALL_GENERATORS.map((g) =>
                validateOne(join(projectDir, g.configFile), g.configFile, fileManager)
            )
        )
    ).filter((p): p is string => p !== null);

    if (problems.length > 0) {
        return error(`Config validation failed: ${problems.join(", ")}`);
    }

    return ok(`All ${ALL_GENERATORS.length} config files validated`);
}
