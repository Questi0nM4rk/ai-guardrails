import { runFormatStage } from "@/hooks/format-stage";
import { runHookEvent } from "@/hooks/run";
import { runSuppressComments } from "@/hooks/suppress-comments";

const HOOK_NAMES = ["run", "suppress-comments", "format-stage"];

export async function runHook(hookName: string, args: string[]): Promise<never> {
  switch (hookName) {
    case "run":
      return runHookEvent();
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
