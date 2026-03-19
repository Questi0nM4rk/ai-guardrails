import { promises as fs } from "node:fs";
import { Glob } from "bun";
import { minimatch } from "minimatch";

function isEnoent(err: unknown): boolean {
  if (typeof err !== "object" || err === null) return false;
  return "code" in err && (err as NodeJS.ErrnoException).code === "ENOENT";
}

export interface FileManager {
  readText(path: string): Promise<string>;
  writeText(path: string, content: string): Promise<void>;
  appendText(path: string, content: string): Promise<void>;
  exists(path: string): Promise<boolean>;
  mkdir(path: string, opts?: { parents?: boolean }): Promise<void>;
  glob(pattern: string, cwd: string, ignore?: readonly string[]): Promise<string[]>;
  isSymlink(path: string): Promise<boolean>;
  delete(path: string): Promise<void>;
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

  async glob(
    pattern: string,
    cwd: string,
    ignore?: readonly string[]
  ): Promise<string[]> {
    const g = new Glob(pattern);
    const results: string[] = [];
    for await (const file of g.scan({ cwd, absolute: false })) {
      results.push(file);
    }
    if (ignore === undefined || ignore.length === 0) return results;
    return results.filter((f) => !ignore.some((ig) => minimatch(f, ig)));
  }

  async isSymlink(path: string): Promise<boolean> {
    try {
      const stat = await fs.lstat(path);
      return stat.isSymbolicLink();
    } catch {
      return false;
    }
  }

  async delete(path: string): Promise<void> {
    try {
      await fs.unlink(path);
    } catch (err: unknown) {
      if (isEnoent(err)) return; // already deleted — idempotent
      throw err;
    }
  }
}
