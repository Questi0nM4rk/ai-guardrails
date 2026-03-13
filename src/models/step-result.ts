export type StepResult =
  | { readonly status: "ok"; readonly message: string }
  | { readonly status: "error"; readonly message: string }
  | { readonly status: "skip"; readonly message: string }
  | { readonly status: "warn"; readonly message: string };

export function ok(message: string): StepResult {
  return { status: "ok", message };
}

export function error(message: string): StepResult {
  return { status: "error", message };
}

export function skip(message: string): StepResult {
  return { status: "skip", message };
}

export function warn(message: string): StepResult {
  return { status: "warn", message };
}
