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
