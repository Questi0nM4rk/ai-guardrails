import type { FileManager } from "@/infra/file-manager";

export class FakeFileManager implements FileManager {
    private readonly files = new Map<string, string>();
    readonly written: Array<[string, string]> = [];
    readonly appended: Array<[string, string]> = [];

    seed(path: string, content: string): void {
        this.files.set(path, content);
    }

    async readText(path: string): Promise<string> {
        const content = this.files.get(path);
        if (content === undefined) {
            throw new Error(`File not found: ${path}`);
        }
        return content;
    }

    async writeText(path: string, content: string): Promise<void> {
        this.files.set(path, content);
        this.written.push([path, content]);
    }

    async appendText(path: string, content: string): Promise<void> {
        const existing = this.files.get(path) ?? "";
        this.files.set(path, existing + content);
        this.appended.push([path, content]);
    }

    async exists(path: string): Promise<boolean> {
        return this.files.has(path);
    }

    async mkdir(_path: string, _opts?: { parents?: boolean }): Promise<void> {
        // no-op for fake
    }

    async glob(pattern: string, _cwd: string): Promise<string[]> {
        const results: string[] = [];
        for (const key of this.files.keys()) {
            if (matchesGlob(key, pattern)) {
                results.push(key);
            }
        }
        return results;
    }

    async isSymlink(_path: string): Promise<boolean> {
        return false;
    }
}

/** Simple glob matching for fake: supports *, **, and {a,b,c} brace expansion */
function matchesGlob(path: string, pattern: string): boolean {
    // Expand {a,b,c} into alternation before converting to regex.
    // Only handles a single brace group per pattern (sufficient for our usage).
    const braceMatch = /\{([^}]+)\}/.exec(pattern);
    if (braceMatch) {
        const group = braceMatch[1];
        if (!group) return false; // malformed pattern
        const alternatives = group.split(",");
        return alternatives.some((alt) =>
            matchesGlob(path, pattern.replace(braceMatch[0], alt))
        );
    }
    const escaped = pattern
        .replace(/[.+^${}()|[\]\\]/g, "\\$&")
        .replace(/\*\*/g, "__DOUBLE_STAR__")
        .replace(/\*/g, "[^/]*")
        .replace(/__DOUBLE_STAR__/g, ".*");
    return new RegExp(`^${escaped}$`).test(path);
}
