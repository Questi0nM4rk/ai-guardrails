import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import type { InstallHint } from "@/runners/types";

function formatHints(hints: ReadonlyArray<{ id: string; hint: InstallHint }>): string {
  return hints
    .map(({ id, hint }) => {
      const cmds = [
        hint.npm,
        hint.pip,
        hint.brew,
        hint.apt,
        hint.cargo,
        hint.go,
        hint.rustup,
      ].filter((c): c is string => c !== undefined);
      const cmdStr = cmds.length > 0 ? cmds[0] : "(see documentation)";
      return `  ${id}: ${hint.description} — ${cmdStr}`;
    })
    .join("\n");
}

export const toolInstallModule: InitModule = {
  id: "tool-install",
  name: "Tool Install",
  description: "Log install hints for missing linter tools",
  category: "tools",
  defaultEnabled: true,
  dependsOn: ["profile-selection"],

  async detect(ctx: InitContext): Promise<boolean> {
    const runners = ctx.languages.flatMap((l) => l.runners());
    const availability = await Promise.all(
      runners.map((r) => r.isAvailable(ctx.commandRunner, ctx.projectDir))
    );
    return availability.some((avail) => !avail);
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const seen = new Set<string>();
    const allRunners = ctx.languages
      .flatMap((l) => l.runners())
      .filter((r) => {
        if (seen.has(r.id)) return false;
        seen.add(r.id);
        return true;
      });

    const results = await Promise.all(
      allRunners.map(async (r) => ({
        id: r.id,
        hint: r.installHint,
        available: await r.isAvailable(ctx.commandRunner, ctx.projectDir),
      }))
    );

    const missing = results.filter((r) => !r.available);

    if (missing.length === 0) {
      return { status: "ok", message: "All tools are already installed" };
    }

    const hints = formatHints(missing);
    ctx.console.info(`Missing tools — install manually:\n${hints}`);

    return {
      status: "ok",
      message: `${missing.length} tool(s) need installation — install hints logged above`,
    };
  },
};
