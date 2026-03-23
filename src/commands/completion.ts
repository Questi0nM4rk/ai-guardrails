const COMMANDS = "init install generate check snapshot status report hook completion";

export function generateBashCompletion(): string {
  return `# bash completion for ai-guardrails
# Source this file or add to ~/.bash_completion.d/
_ai_guardrails() {
  local cur prev
  cur="\${COMP_WORDS[COMP_CWORD]}"
  prev="\${COMP_WORDS[COMP_CWORD-1]}"

  if [ "$COMP_CWORD" -eq 1 ]; then
    COMPREPLY=($(compgen -W "${COMMANDS}" -- "$cur"))
    return
  fi

  case "\${COMP_WORDS[1]}" in
    init)
      COMPREPLY=($(compgen -W "--yes --profile --force --upgrade --interactive --no-hooks --no-ci --no-agent-rules --config-strategy --project-dir" -- "$cur"))
      ;;
    install)
      COMPREPLY=($(compgen -W "--upgrade --project-dir" -- "$cur"))
      ;;
    generate)
      COMPREPLY=($(compgen -W "--check --project-dir" -- "$cur"))
      ;;
    check)
      COMPREPLY=($(compgen -W "--format --baseline --strict --project-dir" -- "$cur"))
      ;;
    snapshot)
      COMPREPLY=($(compgen -W "--baseline --project-dir" -- "$cur"))
      ;;
    status|report)
      COMPREPLY=($(compgen -W "--project-dir" -- "$cur"))
      ;;
    hook)
      COMPREPLY=($(compgen -W "dangerous-cmd protect-configs protect-reads suppress-comments" -- "$cur"))
      ;;
    completion)
      COMPREPLY=($(compgen -W "bash zsh fish" -- "$cur"))
      ;;
    *)
      COMPREPLY=($(compgen -W "--project-dir --quiet --no-color --version --help" -- "$cur"))
      ;;
  esac
}
complete -F _ai_guardrails ai-guardrails
`;
}

export function generateZshCompletion(): string {
  return `#compdef ai-guardrails
_ai_guardrails() {
  local -a commands
  commands=(
    'init:Per-project setup'
    'install:One-time machine setup'
    'generate:Regenerate all managed config files'
    'check:Hold-the-line enforcement'
    'snapshot:Capture current lint state as baseline'
    'status:Project health dashboard'
    'report:Show recent check run history'
    'hook:Internal hook dispatcher'
    'completion:Generate shell completion script'
  )

  local -a global_opts
  global_opts=(
    '--project-dir[Override working directory]:dir:_files -/'
    '--quiet[Suppress info/success output]'
    '--no-color[Disable ANSI color output]'
    '--version[Print version]'
    '--help[Show help]'
  )

  _arguments -C \\
    $global_opts \\
    '1: :->command' \\
    '*: :->args'

  case $state in
    command)
      _describe 'command' commands
      ;;
    args)
      case \${words[2]} in
        init)
          _arguments \\
            '--yes[Accept all defaults]' \\
            '--profile[Set profile]:profile:(strict standard minimal)' \\
            '--force[Overwrite existing managed files]' \\
            '--upgrade[Refresh generated files]' \\
            '--interactive[Prompt for each optional step]' \\
            '--no-hooks[Skip lefthook install]' \\
            '--no-ci[Skip CI workflow generation]' \\
            '--no-agent-rules[Skip AGENTS.md and IDE rule files]' \\
            '--config-strategy[Config handling strategy]:strategy:(merge replace skip)' \\
            '--project-dir[Override working directory]:dir:_files -/'
          ;;
        install)
          _arguments \\
            '--upgrade[Overwrite existing machine config]' \\
            '--project-dir[Override working directory]:dir:_files -/'
          ;;
        generate)
          _arguments \\
            '--check[Verify files are up-to-date]' \\
            '--project-dir[Override working directory]:dir:_files -/'
          ;;
        check)
          _arguments \\
            '--format[Output format]:format:(text sarif)' \\
            '--baseline[Custom baseline path]:file:_files' \\
            '--strict[Ignore baseline]' \\
            '--project-dir[Override working directory]:dir:_files -/'
          ;;
        snapshot)
          _arguments \\
            '--baseline[Custom output path]:file:_files' \\
            '--project-dir[Override working directory]:dir:_files -/'
          ;;
        status|report)
          _arguments \\
            '--project-dir[Override working directory]:dir:_files -/'
          ;;
        hook)
          local -a hooks
          hooks=(
            'dangerous-cmd:Check for dangerous shell commands'
            'protect-configs:Protect managed config files'
            'protect-reads:Protect sensitive file reads'
            'suppress-comments:Remove AI comment markers'
          )
          _describe 'hook' hooks
          ;;
        completion)
          local -a shells
          shells=('bash:Bash completion' 'zsh:Zsh completion' 'fish:Fish completion')
          _describe 'shell' shells
          ;;
      esac
      ;;
  esac
}
_ai_guardrails
`;
}

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

export function runCompletion(shell: string): void {
  switch (shell) {
    case "bash":
      process.stdout.write(generateBashCompletion());
      break;
    case "zsh":
      process.stdout.write(generateZshCompletion());
      break;
    case "fish":
      process.stdout.write(generateFishCompletion());
      break;
    default:
      process.stderr.write(`Unknown shell: ${shell}. Use bash, zsh, or fish.\n`);
      process.exit(1);
  }
}
