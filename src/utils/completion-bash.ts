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
