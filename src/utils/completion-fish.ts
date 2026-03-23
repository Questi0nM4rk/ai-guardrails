export function generateFishCompletion(): string {
  return `# fish completion for ai-guardrails
complete -c ai-guardrails -f

# Subcommands
complete -c ai-guardrails -n '__fish_use_subcommand' -a 'init' -d 'Per-project setup'
complete -c ai-guardrails -n '__fish_use_subcommand' -a 'install' -d 'One-time machine setup'
complete -c ai-guardrails -n '__fish_use_subcommand' -a 'generate' -d 'Regenerate all managed config files'
complete -c ai-guardrails -n '__fish_use_subcommand' -a 'check' -d 'Hold-the-line enforcement'
complete -c ai-guardrails -n '__fish_use_subcommand' -a 'snapshot' -d 'Capture current lint state as baseline'
complete -c ai-guardrails -n '__fish_use_subcommand' -a 'status' -d 'Project health dashboard'
complete -c ai-guardrails -n '__fish_use_subcommand' -a 'report' -d 'Show recent check run history'
complete -c ai-guardrails -n '__fish_use_subcommand' -a 'hook' -d 'Internal hook dispatcher'
complete -c ai-guardrails -n '__fish_use_subcommand' -a 'completion' -d 'Generate shell completion script'

# Global flags
complete -c ai-guardrails -l project-dir -d 'Override working directory' -r
complete -c ai-guardrails -l quiet -d 'Suppress info/success output'
complete -c ai-guardrails -l no-color -d 'Disable ANSI color output'

# init flags
complete -c ai-guardrails -n '__fish_seen_subcommand_from init' -l yes -d 'Accept all defaults'
complete -c ai-guardrails -n '__fish_seen_subcommand_from init' -l profile -d 'Set profile' -r -a 'strict standard minimal'
complete -c ai-guardrails -n '__fish_seen_subcommand_from init' -l force -d 'Overwrite existing managed files'
complete -c ai-guardrails -n '__fish_seen_subcommand_from init' -l upgrade -d 'Refresh generated files'
complete -c ai-guardrails -n '__fish_seen_subcommand_from init' -l interactive -d 'Prompt for each optional step'
complete -c ai-guardrails -n '__fish_seen_subcommand_from init' -l no-hooks -d 'Skip lefthook install'
complete -c ai-guardrails -n '__fish_seen_subcommand_from init' -l no-ci -d 'Skip CI workflow generation'
complete -c ai-guardrails -n '__fish_seen_subcommand_from init' -l no-agent-rules -d 'Skip AGENTS.md and IDE rule files'
complete -c ai-guardrails -n '__fish_seen_subcommand_from init' -l config-strategy -d 'Config handling strategy' -r -a 'merge replace skip'
complete -c ai-guardrails -n '__fish_seen_subcommand_from init' -l project-dir -d 'Override working directory' -r

# install flags
complete -c ai-guardrails -n '__fish_seen_subcommand_from install' -l upgrade -d 'Overwrite existing machine config'
complete -c ai-guardrails -n '__fish_seen_subcommand_from install' -l project-dir -d 'Override working directory' -r

# generate flags
complete -c ai-guardrails -n '__fish_seen_subcommand_from generate' -l check -d 'Verify files are up-to-date'
complete -c ai-guardrails -n '__fish_seen_subcommand_from generate' -l project-dir -d 'Override working directory' -r

# check flags
complete -c ai-guardrails -n '__fish_seen_subcommand_from check' -l format -d 'Output format' -r -a 'text sarif'
complete -c ai-guardrails -n '__fish_seen_subcommand_from check' -l baseline -d 'Custom baseline path' -r
complete -c ai-guardrails -n '__fish_seen_subcommand_from check' -l strict -d 'Ignore baseline'
complete -c ai-guardrails -n '__fish_seen_subcommand_from check' -l project-dir -d 'Override working directory' -r

# snapshot flags
complete -c ai-guardrails -n '__fish_seen_subcommand_from snapshot' -l baseline -d 'Custom output path' -r
complete -c ai-guardrails -n '__fish_seen_subcommand_from snapshot' -l project-dir -d 'Override working directory' -r

# status flags
complete -c ai-guardrails -n '__fish_seen_subcommand_from status' -l project-dir -d 'Override working directory' -r

# report flags
complete -c ai-guardrails -n '__fish_seen_subcommand_from report' -l project-dir -d 'Override working directory' -r

# hook subcommands
complete -c ai-guardrails -n '__fish_seen_subcommand_from hook' -a 'dangerous-cmd' -d 'Check for dangerous shell commands'
complete -c ai-guardrails -n '__fish_seen_subcommand_from hook' -a 'protect-configs' -d 'Protect managed config files'
complete -c ai-guardrails -n '__fish_seen_subcommand_from hook' -a 'protect-reads' -d 'Protect sensitive file reads'
complete -c ai-guardrails -n '__fish_seen_subcommand_from hook' -a 'suppress-comments' -d 'Remove AI comment markers'

# completion subcommands
complete -c ai-guardrails -n '__fish_seen_subcommand_from completion' -a 'bash' -d 'Bash completion'
complete -c ai-guardrails -n '__fish_seen_subcommand_from completion' -a 'zsh' -d 'Zsh completion'
complete -c ai-guardrails -n '__fish_seen_subcommand_from completion' -a 'fish' -d 'Fish completion'
`;
}
