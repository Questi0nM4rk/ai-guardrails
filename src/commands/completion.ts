import {
  generateBashCompletion,
  generateFishCompletion,
  generateZshCompletion,
} from "@/utils/completion-generators";

export { generateBashCompletion, generateFishCompletion, generateZshCompletion };

const SUPPORTED_SHELLS = ["bash", "zsh", "fish"] as const;
type SupportedShell = (typeof SUPPORTED_SHELLS)[number];

function isSupportedShell(shell: string): shell is SupportedShell {
  return (SUPPORTED_SHELLS as readonly string[]).includes(shell);
}

export function getCompletionScript(shell: string): string {
  if (!isSupportedShell(shell)) {
    throw new Error(`Unknown shell: ${shell}. Use bash, zsh, or fish.`);
  }

  const generators: Record<SupportedShell, () => string> = {
    bash: generateBashCompletion,
    zsh: generateZshCompletion,
    fish: generateFishCompletion,
  };

  return generators[shell]();
}
