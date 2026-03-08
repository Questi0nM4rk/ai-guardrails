export interface HookInput {
  session_id: string;
  transcript_path: string;
  cwd: string;
  hook_event_name: "PreToolUse" | "PostToolUse" | "Notification" | "Stop" | string;
  tool_name: string;
  tool_input: Record<string, unknown>;
}

export interface HookOutput {
  hookSpecificOutput: {
    hookEventName: "PreToolUse";
    permissionDecision: "allow" | "deny" | "ask";
    permissionDecisionReason?: string;
  };
}

export interface BashToolInput {
  command: string;
  description?: string;
  restart?: boolean;
}

export interface WriteToolInput {
  file_path: string;
  content?: string;
  old_str?: string;
  new_str?: string;
}
