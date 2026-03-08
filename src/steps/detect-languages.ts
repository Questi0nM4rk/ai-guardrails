import type { FileManager } from "@/infra/file-manager";
import { detectLanguages } from "@/languages/registry";
import type { LanguagePlugin } from "@/languages/types";
import { error, ok } from "@/models/step-result";
import type { StepResult } from "@/models/step-result";

export async function detectLanguagesStep(
  projectDir: string,
  fileManager: FileManager,
): Promise<{ result: StepResult; languages: LanguagePlugin[] }> {
  try {
    const languages = await detectLanguages(projectDir, fileManager);
    const names = languages.map((p) => p.name).join(", ");
    return {
      result: ok(`Detected languages: ${names || "none"}`),
      languages,
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      result: error(`Language detection failed: ${message}`),
      languages: [],
    };
  }
}
