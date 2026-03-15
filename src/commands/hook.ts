import { runDangerousCmd } from "@/hooks/dangerous-cmd";
import { runFormatStage } from "@/hooks/format-stage";
import { runProtectConfigs } from "@/hooks/protect-configs";
import { runProtectReads } from "@/hooks/protect-reads";
import { runSuppressComments } from "@/hooks/suppress-comments";

const HOOK_NAMES = [
  "dangerous-cmd",
  "protect-configs",
  "protect-reads",
  "suppress-comments",
  "format-stage",
];

export async function runHook(hookName: string, args: string[]): Promise<never> {
  switch (hookName) {
    case "dangerous-cmd":
      return runDangerousCmd();
    case "protect-configs":
      return runProtectConfigs();
    case "protect-reads":
      return runProtectReads();
    case "suppress-comments":
      return runSuppressComments(args);
    case "format-stage":
      return runFormatStage();
    default: {
      process.stderr.write(
        `Unknown hook: ${hookName}\nAvailable hooks: ${HOOK_NAMES.join(", ")}\n`
      );
      process.exit(1);
    }
  }
}
