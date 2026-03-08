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

/**
 * Extracts the `command` field from a Bash tool_input record.
 * Returns an empty string when the field is absent or not a string.
 */
export function extractBashCommand(toolInput: Record<string, unknown>): string {
    const cmd = toolInput.command;
    return typeof cmd === "string" ? cmd : "";
}
