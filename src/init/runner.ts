import type { InitContext, InitModule, InitModuleResult } from "@/init/types";

class CircularDependencyError extends Error {
  constructor(remaining: string[]) {
    super(`Circular dependency detected among modules: ${remaining.join(", ")}`);
    this.name = "CircularDependencyError";
  }
}

/**
 * Topological sort using Kahn's algorithm.
 * Throws CircularDependencyError if a cycle is detected.
 */
function topoSort(modules: readonly InitModule[]): InitModule[] {
  const byId = new Map<string, InitModule>(modules.map((m) => [m.id, m]));
  const inDegree = new Map<string, number>(modules.map((m) => [m.id, 0]));
  const dependents = new Map<string, string[]>(modules.map((m) => [m.id, []]));

  for (const mod of modules) {
    for (const dep of mod.dependsOn ?? []) {
      if (!byId.has(dep)) continue; // unknown dep — skip silently
      inDegree.set(mod.id, (inDegree.get(mod.id) ?? 0) + 1);
      const list = dependents.get(dep);
      if (list !== undefined) list.push(mod.id);
    }
  }

  const queue: string[] = [];
  for (const [id, deg] of inDegree) {
    if (deg === 0) queue.push(id);
  }

  const sorted: InitModule[] = [];
  while (queue.length > 0) {
    const id = queue.shift();
    if (id === undefined) break;
    const mod = byId.get(id);
    if (mod !== undefined) sorted.push(mod);
    for (const dependentId of dependents.get(id) ?? []) {
      const newDeg = (inDegree.get(dependentId) ?? 1) - 1;
      inDegree.set(dependentId, newDeg);
      if (newDeg === 0) queue.push(dependentId);
    }
  }

  if (sorted.length !== modules.length) {
    // Find nodes still in cycle
    const remaining = modules
      .filter((m) => !sorted.some((s) => s.id === m.id))
      .map((m) => m.id);
    throw new CircularDependencyError(remaining);
  }

  return sorted;
}

/**
 * Execute a set of init modules in dependency order.
 * Modules not selected (ctx.selections.get(id) !== true) are skipped.
 */
export async function executeModules(
  modules: readonly InitModule[],
  ctx: InitContext
): Promise<InitModuleResult[]> {
  const sorted = topoSort(modules);
  const results: InitModuleResult[] = [];
  const completed = new Set<string>();

  for (const mod of sorted) {
    if (ctx.selections.get(mod.id) !== true) {
      results.push({
        status: "skipped",
        message: `${mod.name}: skipped (not selected)`,
      });
      continue;
    }

    const failedDep = (mod.dependsOn ?? []).find(
      (dep) => ctx.selections.get(dep) === true && !completed.has(dep)
    );
    if (failedDep !== undefined) {
      const result: InitModuleResult = {
        status: "skipped",
        message: `${mod.name}: skipped (dependency ${failedDep} did not complete successfully)`,
      };
      ctx.console.info(`[${mod.name}] ${result.message}`);
      results.push(result);
      continue;
    }

    ctx.console.step(`[${mod.name}] ${mod.description}`);

    let result: InitModuleResult;
    try {
      result = await mod.execute(ctx);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e);
      result = { status: "error", message: `[${mod.name}] crashed: ${message}` };
    }

    if (result.status === "ok") {
      ctx.console.success(`[${mod.name}] ${result.message}`);
      completed.add(mod.id);
    } else if (result.status === "skipped") {
      ctx.console.info(`[${mod.name}] ${result.message}`);
    } else {
      ctx.console.error(`[${mod.name}] ${result.message}`);
    }

    results.push(result);
  }

  return results;
}
