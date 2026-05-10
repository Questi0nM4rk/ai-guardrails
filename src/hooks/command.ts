// Shared between the project-local generator (.claude/settings.json) and the
// global install step (~/.claude/settings.json). Both wire the same hook.
//
// Fail-open if either binary is missing (silent allow, exit 0). Otherwise
// route escalations through hook-kit's broker so risky-command approvals
// stay out of Claude's ask UI — listeners up the parent session chain decide.
export const HOOK_COMMAND =
  "command -v ai-guardrails >/dev/null 2>&1 || exit 0; " +
  "command -v hook-kit >/dev/null 2>&1 || exit 0; " +
  "HOOK_KIT_ASKPASS='hook-kit broker --askpass' ai-guardrails hook run";
