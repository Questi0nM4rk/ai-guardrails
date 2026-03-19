import type { LanguagePlugin } from "@/languages/types";

/** Create a minimal fake LanguagePlugin for testing */
export function makePlugin(id: string): LanguagePlugin {
  return { id, name: id, detect: async () => true, runners: () => [] };
}
