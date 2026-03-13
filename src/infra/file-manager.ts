import { promises as fs } from "node:fs";
import { Glob } from "bun";

export interface FileManager {
  readText(path: string): Promise<string>;
  writeText(path: string, content: string): Promise<void>;
  appendText(path: string, content: string): Promise<void>;
  exists(path: string): Promise<boolean>;
  mkdir(path: string, opts?: { parents?: boolean }): Promise<void>;
  glob(pattern: string, cwd: string): Promise<string[]>;
  isSymlink(path: string): Promise<boolean>;
}

export class RealFileManager implements FileManager {
  async readText(path: string): Promise<string> {
    return fs.readFile(path, "utf8");
  }

  async writeText(path: string, content: string): Promise<void> {
    await fs.writeFile(path, content, "utf8");
  }

  async appendText(path: string, content: string): Promise<void> {
    await fs.appendFile(path, content, "utf8");
  }

  async exists(path: string): Promise<boolean> {
    try {
      await fs.access(path);
      return true;
    } catch {
      return false;
    }
  }

  async mkdir(path: string, opts?: { parents?: boolean }): Promise<void> {
    await fs.mkdir(path, { recursive: opts?.parents ?? false });
  }

  async glob(pattern: string, cwd: string): Promise<string[]> {
    const g = new Glob(pattern);
    const results: string[] = [];
    for await (const file of g.scan({ cwd, absolute: false })) {
      results.push(file);
    }
    return results;
  }

  async isSymlink(path: string): Promise<boolean> {
    try {
      const stat = await fs.lstat(path);
      return stat.isSymbolicLink();
    } catch {
      return false;
    }
  }
}
