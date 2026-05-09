// Translator: AG rule shape → hook-kit modules.

import type { HookEvent, evaluate as hkEvaluate, Rule } from "@questi0nm4rk/hook-kit";
import {
  cmd,
  createModule,
  type HookModule,
  path,
  pipe,
  redirect,
} from "@questi0nm4rk/hook-kit";
import type {
  CallRule,
  CheckResult,
  CommandRule,
  PathRule,
  PipeRule,
  RedirectRule,
  RuleDecision,
  RuleSet,
  ToolEvent,
} from "@/check/types";

const TOOL_BY_EVENT_TYPE = {
  bash: "Bash",
  write: "Write",
  read: "Read",
} as const;

function toHookKitTerminal(
  builder: {
    deny: (r: string, l?: string) => Rule;
    escalate: (r: string, l?: string) => Rule;
  },
  decision: RuleDecision,
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
  return toHookKitTerminal(b, r.decision, r.reason, label);
}

function pipeToHkRule(r: PipeRule, label: string): Rule {
  return toHookKitTerminal(pipe(r.from, r.into), r.decision, r.reason, label);
}

function redirectToHkRule(r: RedirectRule, label: string): Rule {
  const b = r.pathPattern !== undefined ? redirect(r.pathPattern) : redirect();
  return toHookKitTerminal(b, r.decision, r.reason, label);
}

/** `recurse` is handled natively by hook-kit's engine (default-on), so it's a
 *  no-op in the translator. */
export function toCommandModule(
  rules: readonly CommandRule[],
  label: string
): HookModule {
  const hkRules: Rule[] = [];
  for (const r of rules) {
    if (r.kind === "call") hkRules.push(callToCmdRule(r, label));
    else if (r.kind === "pipe") hkRules.push(pipeToHkRule(r, label));
    else if (r.kind === "redirect") hkRules.push(redirectToHkRule(r, label));
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

export function toPathModules(rules: readonly PathRule[], label: string): HookModule[] {
  const writeRules: Rule[] = [];
  const readRules: Rule[] = [];
  const redirectRules: Rule[] = [];
  for (const r of rules) {
    if (r.event === "write" || r.event === "both") {
      writeRules.push(
        toHookKitTerminal(path(r.pattern).onWrite(), r.decision, r.reason, label)
      );
      // Bash redirect protection: `cmd > path` whose target matches a write
      // pattern is caught the same way path() catches Edit/Write.
      redirectRules.push(
        toHookKitTerminal(redirect(r.pattern), r.decision, r.reason, label)
      );
    }
    if (r.event === "read" || r.event === "both") {
      readRules.push(
        toHookKitTerminal(path(r.pattern).onRead(), r.decision, r.reason, label)
      );
    }
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

export function buildAllModules(ruleset: RuleSet, label: string): HookModule[] {
  return [
    toCommandModule(ruleset.commandRules, label),
    ...toPathModules(ruleset.pathRules, label),
  ];
}

export function fromHookKit(
  decision: Awaited<ReturnType<typeof hkEvaluate>>
): CheckResult {
  if (decision === null) return { decision: "allow" };
  if (decision.kind === "deny") return { decision: "deny", reason: decision.reason };
  if (decision.kind === "escalate") return { decision: "ask", reason: decision.reason };
  // context decisions don't gate the tool call — treat as allow.
  return { decision: "allow" };
}

/** Build a synthetic HookEvent for in-process evaluation (BDD steps and the
 *  `isDangerous` Bash convenience). The wire-protocol path uses
 *  claudeCodeAdapter, which constructs HookEvents from real stdin instead. */
export function synthesizeHookEvent(event: ToolEvent, sessionId: string): HookEvent {
  const base = {
    eventName: "PreToolUse" as const,
    sessionId,
    cwd: process.cwd(),
    transcriptPath: "",
    raw: {},
  };
  if (event.type === "bash") {
    return {
      ...base,
      toolName: TOOL_BY_EVENT_TYPE.bash,
      toolInput: { command: event.command },
    };
  }
  return {
    ...base,
    toolName: TOOL_BY_EVENT_TYPE[event.type],
    toolInput: { file_path: event.path },
  };
}
