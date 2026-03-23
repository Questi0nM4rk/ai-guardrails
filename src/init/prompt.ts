import type { Interface as ReadlineInterface } from "node:readline";

type CreateReadline = () => ReadlineInterface;

/** Minimal subset of readline.Interface used by prompt helpers. */
export interface ReadlineHandle {
  question(query: string, callback: (answer: string) => void): void;
  close(): void;
}

async function ask(rl: ReadlineHandle, question: string): Promise<string> {
  return new Promise((resolve) => {
    rl.question(question, resolve);
  });
}

function toHandle(createReadline: CreateReadline): ReadlineHandle {
  // ReadlineInterface satisfies ReadlineHandle — it has question() and close().
  // We narrow to our minimal interface here so prompt helpers stay testable.
  return createReadline();
}

/**
 * Ask a yes/no question. Returns true for "y"/"yes", false for "n"/"no".
 * Empty input uses defaultYes to decide.
 */
export async function askYesNo(
  createReadline: CreateReadline,
  question: string,
  defaultYes: boolean
): Promise<boolean> {
  const hint = defaultYes ? "[Y/n]" : "[y/N]";
  const rl = toHandle(createReadline);
  try {
    const input = await ask(rl, `${question} ${hint}: `);
    const trimmed = input.trim().toLowerCase();
    if (trimmed === "") return defaultYes;
    return trimmed === "y" || trimmed === "yes";
  } finally {
    rl.close();
  }
}

/**
 * Ask a multiple-choice question. Loops until valid input or empty (uses defaultChoice).
 */
export async function askChoice<T extends string>(
  createReadline: CreateReadline,
  question: string,
  choices: readonly T[],
  defaultChoice: T
): Promise<T> {
  const hint = choices.join("/");
  const rl = toHandle(createReadline);
  try {
    let prompt = `${question} [${hint}] (default: ${defaultChoice}): `;
    for (;;) {
      const input = await ask(rl, prompt);
      const trimmed = input.trim().toLowerCase();
      if (trimmed === "") return defaultChoice;
      const match = choices.find((c) => c === trimmed);
      if (match !== undefined) return match;
      prompt = `Invalid. Choose ${hint} (default: ${defaultChoice}): `;
    }
  } finally {
    rl.close();
  }
}

/**
 * Ask a free-text question. Empty input returns defaultValue.
 */
export async function askText(
  createReadline: CreateReadline,
  question: string,
  defaultValue: string
): Promise<string> {
  const rl = toHandle(createReadline);
  try {
    const hint = defaultValue ? ` (default: ${defaultValue})` : "";
    const input = await ask(rl, `${question}${hint}: `);
    const trimmed = input.trim();
    return trimmed === "" ? defaultValue : trimmed;
  } finally {
    rl.close();
  }
}

/**
 * Ask for a comma-separated list. Returns empty array on empty input.
 */
export async function askCommaSeparated(
  createReadline: CreateReadline,
  question: string
): Promise<string[]> {
  const rl = toHandle(createReadline);
  try {
    const input = await ask(rl, `${question}: `);
    const trimmed = input.trim();
    if (trimmed === "") return [];
    return trimmed
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  } finally {
    rl.close();
  }
}

/**
 * Ask how to handle a file conflict: merge, skip, or replace.
 */
export async function askFileConflict(
  createReadline: CreateReadline,
  filename: string
): Promise<"merge" | "skip" | "replace"> {
  const choices = ["merge", "skip", "replace"] as const;
  return askChoice(createReadline, `${filename} already exists`, choices, "skip");
}
