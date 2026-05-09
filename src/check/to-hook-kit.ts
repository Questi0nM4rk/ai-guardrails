// Translate ai-guardrails' rule representation into hook-kit modules so the
// existing rule-group definitions (callRule/pipeRule/redirectRule) can drive
// hook-kit's evaluate() without rewriting the rule files.
//
// This is the bridge for the walking-skeleton dogfood: keep the rule
// definitions stable, swap the engine underneath.

import type { Rule } from "@questi0nm4rk/hook-kit";
import {
  cmd,
  createModule,
  escalate,
  type HookModule,
  path,
  pipe,
  redirect,
} from "@questi0nm4rk/hook-kit";
import type {
  CallRule,
  CommandRule,
  PathRule,
  PipeRule,
  RedirectRule,
} from "@/check/types";

/** Map AG's CheckDecision → a hook-kit Decision builder.
 *  AG's "ask" maps to hook-kit's `escalate` (which delegates to harness UI
 *  when no askpass is configured — same UX as AG's old `ask` JSON output). */
function toHookKitTerminal(
  builder: {
    deny: (r: string, l?: string) => Rule;
    escalate: (r: string, l?: string) => Rule;
  },
  decision: "ask" | "deny",
  reason: string,
  label: string
): Rule {
  return decision === "deny"
    ? builder.deny(reason, label)
    : builder.escalate(reason, label);
}

function callToCmdRule(r: CallRule, label: string): Rule {
  let b = cmd(r.cmd, ...(r.sub !== undefined ? [r.sub] : []));
  for (const f of r.flags ?? []) b = b.withFlag(f);
  for (const f of r.noFlags ?? []) b = b.withoutFlag(f);
  for (const a of r.args ?? []) b = b.argIncludes(a);
  if (r.hasDdash === true) b = b.withDdash();
  return toHookKitTerminal(
    b,
    r.decision === "allow" ? "ask" : r.decision,
    r.reason,
    label
  );
}

function pipeToHkRule(r: PipeRule, label: string): Rule {
  return toHookKitTerminal(
    pipe(r.from, r.into),
    r.decision === "allow" ? "ask" : r.decision,
    r.reason,
    label
  );
}

function redirectToHkRule(r: RedirectRule, label: string): Rule {
  const b = r.pathPattern !== undefined ? redirect(r.pathPattern) : redirect();
  return toHookKitTerminal(
    b,
    r.decision === "allow" ? "ask" : r.decision,
    r.reason,
    label
  );
}

/** Convert AG command rules into a single hook-kit Bash module. The `recurse`
 *  rule is a no-op here — hook-kit's engine recurses inline shells by default. */
export function toCommandModule(
  rules: readonly CommandRule[],
  label: string
): HookModule {
  const hkRules: Rule[] = [];
  for (const r of rules) {
    if (r.kind === "call") hkRules.push(callToCmdRule(r, label));
    else if (r.kind === "pipe") hkRules.push(pipeToHkRule(r, label));
    else if (r.kind === "redirect") hkRules.push(redirectToHkRule(r, label));
    // r.kind === "recurse" — handled natively by hook-kit's engine (default-on)
  }
  return createModule(
    {
      id: "ai-guardrails-bash",
      name: "ai-guardrails Bash rules",
      events: ["PreToolUse"],
      matchers: ["Bash"],
    },
    hkRules
  );
}

/** Convert AG path rules into hook-kit Edit/Write/NotebookEdit + Read modules.
 *  AG's `event: "both"` becomes the path()-default both-events behavior. */
export function toPathModules(rules: readonly PathRule[], label: string): HookModule[] {
  const writeRules: Rule[] = [];
  const readRules: Rule[] = [];
  for (const r of rules) {
    const reason = r.reason;
    if (r.event === "write" || r.event === "both") {
      const b = path(r.pattern).onWrite();
      writeRules.push(
        r.decision === "deny" ? b.deny(reason, label) : b.escalate(reason, label)
      );
    }
    if (r.event === "read" || r.event === "both") {
      const b = path(r.pattern).onRead();
      readRules.push(
        r.decision === "deny" ? b.deny(reason, label) : b.escalate(reason, label)
      );
    }
  }
  // Also surface as Bash redirect protection: any `cmd > path` whose target
  // matches a write-rule pattern is caught the same way path() catches Edit/Write.
  const redirectRules: Rule[] = [];
  for (const r of rules) {
    if (r.event !== "write" && r.event !== "both") continue;
    redirectRules.push(
      r.decision === "deny"
        ? redirect(r.pattern).deny(r.reason, label)
        : redirect(r.pattern).escalate(r.reason, label)
    );
  }

  const modules: HookModule[] = [];
  if (writeRules.length > 0) {
    modules.push(
      createModule(
        {
          id: "ai-guardrails-paths-write",
          name: "ai-guardrails write protection",
          events: ["PreToolUse"],
          matchers: ["Edit", "Write", "NotebookEdit"],
        },
        writeRules
      )
    );
  }
  if (readRules.length > 0) {
    modules.push(
      createModule(
        {
          id: "ai-guardrails-paths-read",
          name: "ai-guardrails read protection",
          events: ["PreToolUse"],
          matchers: ["Read"],
        },
        readRules
      )
    );
  }
  if (redirectRules.length > 0) {
    modules.push(
      createModule(
        {
          id: "ai-guardrails-redirects",
          name: "ai-guardrails Bash redirect protection",
          events: ["PreToolUse"],
          matchers: ["Bash"],
        },
        redirectRules
      )
    );
  }
  return modules;
}

// Re-export for callers; quiets unused-import warnings in the wrapper above.
export { escalate };
