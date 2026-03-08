import { minimatch } from "minimatch";
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
      const err = Object.assign(new Error(`ENOENT: no such file or directory, open '${path}'`), {
        code: "ENOENT",
      });
      throw err;
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

  async glob(pattern: string, cwd: string): Promise<string[]> {
    const matched = [...this.files.keys()].filter((p) => {
      const rel = p.startsWith(cwd) ? p.slice(cwd.length).replace(/^\//, "") : p;
      return minimatch(rel, pattern);
    });
    return matched;
  }

  async isSymlink(_path: string): Promise<boolean> {
    return false;
  }
}
