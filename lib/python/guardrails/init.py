"""Project initialization for ai-guardrails.

Replaces the bash ``ai-guardrails-init`` script with a modular Python
implementation.  Responsible for:

- Detecting project languages
- Copying base and language-specific configs
- Assembling ``.pre-commit-config.yaml``
- Installing Claude Code PreToolUse hooks
- Scaffolding the exception registry and generating configs
- Installing CI workflows, CodeRabbit config, and agent instructions
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import typing
from pathlib import Path

from guardrails._paths import find_configs_dir, find_lib_dir, find_templates_dir
from guardrails.constants import BLUE, GREEN, NC, RED, YELLOW

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language → config file mapping
# ---------------------------------------------------------------------------
_LANG_CONFIGS: dict[str, list[str]] = {
    "python": ["ruff.toml"],
    "rust": ["rustfmt.toml"],
    "dotnet": ["Directory.Build.props", ".globalconfig"],
    "cpp": [".clang-format"],
    "lua": ["stylua.toml"],
    "node": ["biome.json"],
    # go and shell: no config files, just pre-commit hooks
}

_ALL_LANG_CONFIGS: list[str] = [name for names in _LANG_CONFIGS.values() for name in names]

# Hook scripts to copy into .ai-guardrails/hooks/
_HOOK_SCRIPTS: list[str] = [
    "format-and-stage.sh",
    "detect-suppression-comments.sh",
    "validate-generated-configs.sh",
    "protect-generated-configs.sh",
    "detect-config-ignore-edits.sh",
    "dangerous-command-check.sh",
    "pre-commit.sh",
    "pre-push.sh",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_ok(msg: str) -> None:
    print(f"  {GREEN}\u2713{NC} {msg}")


def _print_skip(msg: str) -> None:
    print(f"  {YELLOW}\u2298 {msg}{NC}")


def _print_warn(msg: str) -> None:
    print(f"  {YELLOW}\u26a0 {msg}{NC}")


def _print_fail(msg: str) -> None:
    print(f"  {RED}\u2717 {msg}{NC}")


def _copy_config(src: Path, dst: Path, *, force: bool) -> None:
    """Copy a single config file, respecting --force."""
    if dst.exists():
        if not force:
            _print_skip(f"{dst.name} exists (use --force to overwrite)")
            return
        # Backup before overwriting
        backup = dst.with_suffix(dst.suffix + ".bak")
        shutil.copy2(dst, backup)

    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        _print_ok(dst.name)
    else:
        _print_fail(f"{src.name} not found")


def _is_github_project(project_dir: Path) -> bool:
    """Check if the project appears to be hosted on GitHub."""
    if (project_dir / ".github").is_dir():
        return True
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            check=False,
        )
    except FileNotFoundError:
        return False
    else:
        return "github.com" in result.stdout


def _detect_python_deps(project_dir: Path) -> str:
    """Auto-detect Python dependency management tool.

    Returns:
        ``"uv"``, ``"pip"``, or ``"none"``.
    """
    if (project_dir / "uv.lock").exists():
        return "uv"
    if (project_dir / "requirements.txt").exists():
        return "pip"
    if (project_dir / "pyproject.toml").exists():
        return "pip"
    return "none"


# ---------------------------------------------------------------------------
# Copy configs
# ---------------------------------------------------------------------------


def _copy_base_configs(configs_dir: Path, project_dir: Path, *, force: bool) -> None:
    """Always-installed configs (.editorconfig, .markdownlint.jsonc)."""
    _copy_config(configs_dir / ".editorconfig", project_dir / ".editorconfig", force=force)
    _copy_config(
        configs_dir / ".markdownlint.jsonc",
        project_dir / ".markdownlint.jsonc",
        force=force,
    )


def _copy_language_configs(
    configs_dir: Path,
    project_dir: Path,
    *,
    languages: list[str],
    force: bool,
) -> None:
    """Copy language-specific config files."""
    for lang in languages:
        for name in _LANG_CONFIGS.get(lang, []):
            _copy_config(configs_dir / name, project_dir / name, force=force)


# ---------------------------------------------------------------------------
# Pre-commit setup
# ---------------------------------------------------------------------------


def _setup_precommit(
    lib_dir: Path,
    project_dir: Path,
    *,
    languages: list[str],
    force: bool,
    pip_audit_mode: str,
) -> None:
    """Assemble pre-commit config, copy hooks, and install."""
    print()
    print(f"{GREEN}Setting up pre-commit...{NC}")

    configure_pip_audit = not (project_dir / ".pre-commit-config.yaml").exists() or force

    # Generate pre-commit config via assemble module
    if (project_dir / ".pre-commit-config.yaml").exists() and not force:
        _print_skip(".pre-commit-config.yaml exists (use --force to overwrite)")
    else:
        from guardrails.assemble import main as assemble_main

        output_path = str(project_dir / ".pre-commit-config.yaml")
        assemble_args = ["--project-dir", str(project_dir), "--output", output_path]
        if languages:
            assemble_args.extend(["--languages", *languages])

        if assemble_main(assemble_args) == 0:
            _print_ok(".pre-commit-config.yaml")

            # Configure pip-audit for Python projects
            if configure_pip_audit and _has_python(languages):
                if pip_audit_mode == "auto":
                    pip_audit_mode = _detect_python_deps(project_dir)
                _configure_pip_audit(pip_audit_mode, project_dir)
        else:
            _print_fail("Failed to generate .pre-commit-config.yaml")

    # Copy hook scripts to .ai-guardrails/hooks/
    hooks_dir = project_dir / ".ai-guardrails" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    src_hooks = lib_dir / "hooks"
    for script in _HOOK_SCRIPTS:
        src = src_hooks / script
        if src.exists():
            dst = hooks_dir / script
            shutil.copy2(src, dst)
            dst.chmod(0o755)
            _print_ok(script)

    # Copy Python package for hook shims
    src_python = lib_dir / "python" / "guardrails"
    dst_python = project_dir / ".ai-guardrails" / "lib" / "python" / "guardrails"
    if src_python.is_dir():
        if dst_python.exists():
            shutil.rmtree(dst_python)
        shutil.copytree(src_python, dst_python)
        _print_ok("lib/python/guardrails (hook runtime)")

    # Install Claude Code PreToolUse hooks
    _install_claude_hook()
    _install_dangerous_cmd_hook()

    # Fix pre-commit config paths for local hooks
    precommit_cfg = project_dir / ".pre-commit-config.yaml"
    if precommit_cfg.exists():
        content = precommit_cfg.read_text()
        content = content.replace(
            "entry: lib/hooks/format-and-stage.sh",
            "entry: .ai-guardrails/hooks/format-and-stage.sh",
        )
        content = content.replace(
            "entry: lib/hooks/detect-suppression-comments.sh",
            "entry: .ai-guardrails/hooks/detect-suppression-comments.sh",
        )
        precommit_cfg.write_text(content)

    # Install pre-commit hooks
    _install_precommit_hooks(project_dir)


def _has_python(languages: list[str]) -> bool:
    return "python" in languages


def _configure_pip_audit(mode: str, project_dir: Path) -> None:
    """Append pip-audit block to .pre-commit-config.yaml."""
    config_file = project_dir / ".pre-commit-config.yaml"
    if not config_file.exists():
        return

    block = ""
    if mode == "uv":
        # Try to export uv.lock
        try:
            subprocess.run(
                [
                    "uv",
                    "export",
                    "--format",
                    "requirements.txt",
                    "--output-file",
                    "requirements-audit.txt",
                    "--quiet",
                ],
                check=True,
                capture_output=True,
                cwd=project_dir,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            _print_warn("Could not export uv.lock - pip-audit disabled")
            return

        block = """
  # pip-audit - CVE scanning for Python dependencies
  - repo: https://github.com/pypa/pip-audit
    rev: v2.10.0
    hooks:
      - id: pip-audit
        name: "python - pip-audit CVE scan"
        args: ["--strict", "--progress-spinner", "off", "-r", "requirements-audit.txt"]"""
        _print_ok("Configured pip-audit for uv (-r requirements-audit.txt)")

    elif mode == "pip":
        req_flag = "-r requirements.txt" if (project_dir / "requirements.txt").exists() else "."
        block = f"""
  # pip-audit - CVE scanning for Python dependencies
  - repo: https://github.com/pypa/pip-audit
    rev: v2.10.0
    hooks:
      - id: pip-audit
        name: "python - pip-audit CVE scan"
        args: ["--strict", "--progress-spinner", "off", "{req_flag}"]"""
        _print_ok(f"Configured pip-audit for pip ({req_flag})")

    elif mode == "none":
        _print_warn("pip-audit disabled")
        return

    if block:
        with config_file.open("a") as f:
            f.write(block)


def _install_pretooluse_hook(
    *,
    hook_cmd: str,
    matcher: str,
    check_substring: str,
    label: str,
) -> None:
    """Install a PreToolUse hook in ``~/.claude/settings.json``.

    Args:
        hook_cmd: Shell command to run as the hook.
        matcher: Tool matcher pattern (e.g. ``"Bash"``).
        check_substring: Substring to detect duplicates.
        label: Human-readable label for status messages.

    """
    settings_path = Path.home() / ".claude" / "settings.json"

    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            settings = {}
        existing_hooks = settings.get("hooks", {}).get("PreToolUse", [])
        for entry in existing_hooks:
            for h in entry.get("hooks", []):
                if check_substring in h.get("command", ""):
                    _print_skip(f"{label} already installed")
                    return
    else:
        settings = {}

    hook_entry = {
        "matcher": matcher,
        "hooks": [{"type": "command", "command": hook_cmd}],
    }

    hooks = settings.setdefault("hooks", {})
    pre_tool_use = hooks.setdefault("PreToolUse", [])
    pre_tool_use.append(hook_entry)

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    if settings_path.exists():
        backup_path = settings_path.with_suffix(".json.bak")
        shutil.copy2(settings_path, backup_path)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    _print_ok(f"{label} installed")


def _install_claude_hook() -> None:
    """Install the protect-generated-configs PreToolUse hook."""
    _install_pretooluse_hook(
        hook_cmd="~/.ai-guardrails/hooks/protect-generated-configs.sh",
        matcher="Write|Edit",
        check_substring="protect-generated-configs",
        label="Claude Code PreToolUse hook",
    )


def _install_dangerous_cmd_hook() -> None:
    """Install the dangerous-command-check PreToolUse hook."""
    _install_pretooluse_hook(
        hook_cmd="~/.ai-guardrails/hooks/dangerous-command-check.sh",
        matcher="Bash",
        check_substring="dangerous-command-check",
        label="Dangerous command check hook",
    )


def _install_precommit_hooks(project_dir: Path) -> None:
    """Run ``pre-commit install`` if available."""
    if not (project_dir / ".git").is_dir():
        return

    if not shutil.which("pre-commit"):
        print(f"  {YELLOW}Note: Install pre-commit to activate hooks:{NC}")
        print("    pip install pre-commit && pre-commit install")
        return

    # Fix potential empty hooksPath
    try:
        result = subprocess.run(
            ["git", "config", "core.hooksPath"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip() == "":
            subprocess.run(
                ["git", "config", "--unset", "core.hooksPath"],
                capture_output=True,
                cwd=project_dir,
                check=False,
            )
            _print_warn("Fixed empty core.hooksPath setting")
    except FileNotFoundError:
        _log.debug("git not found, skipping hooksPath fix")

    for hook_type_args in [[], ["--hook-type", "commit-msg"]]:
        try:
            subprocess.run(
                ["pre-commit", "install", *hook_type_args],
                capture_output=True,
                cwd=project_dir,
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            _log.debug("pre-commit install failed for %s", hook_type_args)
        else:
            label = "commit-msg hook" if hook_type_args else "pre-commit hooks"
            _print_ok(f"{label} installed")

    # Verify
    if (project_dir / ".git" / "hooks" / "pre-commit").exists():
        _print_ok("Hooks verified in .git/hooks/")
    else:
        _print_fail("Warning: pre-commit hook not found in .git/hooks/")
        print(f"  {YELLOW}  Try: pre-commit install --force{NC}")


# ---------------------------------------------------------------------------
# Gitignore, registry, CI, CodeRabbit, agent instructions
# ---------------------------------------------------------------------------


def _add_to_gitignore(project_dir: Path) -> None:
    """Add .ai-guardrails/ to .gitignore if missing."""
    if not (project_dir / ".git").is_dir():
        return

    gitignore = project_dir / ".gitignore"
    marker = ".ai-guardrails/"
    if gitignore.exists() and marker in gitignore.read_text():
        return

    # Ensure we start on a new line if the file doesn't end with a newline
    prefix = ""
    if gitignore.exists() and gitignore.stat().st_size > 0:
        existing = gitignore.read_text()
        if not existing.endswith("\n"):
            prefix = "\n"

    with gitignore.open("a") as f:
        f.write(f"{prefix}{marker}\n")
    _print_ok("Added .ai-guardrails/ to .gitignore")


def _scaffold_registry(templates_dir: Path, project_dir: Path, *, force: bool) -> None:
    """Copy exception registry template if not present."""
    src = templates_dir / "guardrails-exceptions.toml"
    dst = project_dir / ".guardrails-exceptions.toml"
    if not src.exists():
        return
    if dst.exists() and not force:
        return
    shutil.copy2(src, dst)
    _print_ok(".guardrails-exceptions.toml")


def _generate_from_registry(project_dir: Path) -> None:
    """Generate merged configs from exception registry."""
    if not (project_dir / ".guardrails-exceptions.toml").exists():
        return

    try:
        from guardrails.generate import run_generate_configs
    except ImportError:
        _log.debug("generate module unavailable (missing tomli-w/tomlkit)")
        return

    if run_generate_configs(project_dir=str(project_dir)):
        _print_ok("Generated configs from exception registry")
    else:
        _print_warn("Config generation failed (check .guardrails-exceptions.toml)")


def _install_ci_workflow(templates_dir: Path, project_dir: Path, *, force: bool) -> None:
    """Install check.yml CI workflow."""
    print()
    print(f"{GREEN}Setting up CI workflow...{NC}")
    workflows = project_dir / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    src = templates_dir / "workflows" / "check.yml"
    if src.exists():
        _copy_config(src, workflows / "check.yml", force=force)
    else:
        _print_warn("CI workflow template not found")


def _install_claude_review(templates_dir: Path, project_dir: Path, *, force: bool) -> None:
    """Install Claude Code review workflow."""
    print()
    print(f"{GREEN}Setting up Claude Code review...{NC}")
    workflows = project_dir / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    src = templates_dir / "workflows" / "claude-review.yml"
    if src.exists():
        _copy_config(src, workflows / "claude-review.yml", force=force)
        print(f"  {BLUE}\u2192 Note: Requires OIDC auth (must be on default branch first){NC}")
    else:
        _print_warn("Claude review workflow template not found")


def _install_coderabbit(templates_dir: Path, project_dir: Path, *, force: bool) -> None:
    """Install CodeRabbit config."""
    print()
    print(f"{GREEN}Setting up CodeRabbit...{NC}")
    src = templates_dir / ".coderabbit.yaml"
    if src.exists():
        _copy_config(src, project_dir / ".coderabbit.yaml", force=force)
        print(
            f"  {BLUE}\u2192 Customize path_instructions in .coderabbit.yaml for your project{NC}"
        )
    else:
        _print_warn("CodeRabbit config template not found")


def _install_gemini(templates_dir: Path, project_dir: Path, *, force: bool) -> None:
    """Install Gemini Code Assist config (.gemini/ directory)."""
    print()
    print(f"{GREEN}Setting up Gemini Code Assist...{NC}")
    src_dir = templates_dir / ".gemini"
    if not src_dir.is_dir():
        _print_warn("Gemini config template not found")
        return

    dst_dir = project_dir / ".gemini"
    dst_dir.mkdir(parents=True, exist_ok=True)

    for src_file in src_dir.iterdir():
        if src_file.is_file():
            _copy_config(src_file, dst_dir / src_file.name, force=force)

    print(f"  {BLUE}\u2192 Install the Gemini Code Assist GitHub App to activate{NC}")


def _install_deepsource(templates_dir: Path, project_dir: Path, *, force: bool) -> None:
    """Install DeepSource config (.deepsource.toml)."""
    print()
    print(f"{GREEN}Setting up DeepSource...{NC}")
    src = templates_dir / ".deepsource.toml"
    if src.exists():
        _copy_config(src, project_dir / ".deepsource.toml", force=force)
        print(f"  {BLUE}\u2192 Activate DeepSource in GitHub Marketplace to enable analysis{NC}")
    else:
        _print_warn("DeepSource config template not found")


def _setup_agent_instructions(templates_dir: Path, project_dir: Path) -> None:
    """Append guardrails rules to CLAUDE.md or AGENTS.md."""
    marker = "## AI Guardrails - Code Standards"
    template = templates_dir / "CLAUDE.md.guardrails"
    if not template.exists():
        return

    print()
    print(f"{GREEN}Setting up agent instructions...{NC}")

    template_content = template.read_text()

    def _append(filepath: Path) -> None:
        existing = filepath.read_text() if filepath.exists() else ""
        if marker in existing:
            _print_skip(f"{filepath.name} already has guardrails section")
            return
        prefix = ""
        if existing and not existing.endswith("\n"):
            prefix = "\n"
        with filepath.open("a") as f:
            f.write(f"{prefix}\n{template_content}")
        _print_ok(f"Appended guardrails rules to {filepath.name}")

    agents_md = project_dir / "AGENTS.md"
    claude_md = project_dir / "CLAUDE.md"

    if agents_md.exists():
        _append(agents_md)
    if claude_md.exists():
        _append(claude_md)
    elif not agents_md.exists():
        content = f"# Project Instructions\n{template_content}"
        if not content.endswith("\n"):
            content += "\n"
        claude_md.write_text(content)
        _print_ok("Created CLAUDE.md with guardrails rules")


# ---------------------------------------------------------------------------
# Dry-run report
# ---------------------------------------------------------------------------


def _dry_run_report(
    project_dir: Path,
    *,
    languages: list[str],
    project_type: str,
    skip_precommit: bool,
    install_ci: str,
    install_claude_review: str,
    install_coderabbit: str,
    install_gemini: str,
    install_deepsource: str,
) -> None:
    """Print what ``run_init`` would do without making changes."""

    def _would(action: str) -> None:
        print(f"  {YELLOW}would{NC} {action}")

    # Base configs
    print(f"\n{GREEN}Configs:{NC}")
    _would("copy .editorconfig")
    _would("copy .markdownlint.jsonc")
    if project_type == "all":
        for name in _ALL_LANG_CONFIGS:
            _would(f"copy {name}")
    else:
        for lang in languages:
            for name in _LANG_CONFIGS.get(lang, []):
                _would(f"copy {name}")

    # Pre-commit
    if not skip_precommit:
        print(f"\n{GREEN}Pre-commit:{NC}")
        _would("assemble .pre-commit-config.yaml")
        _would("copy hook scripts to .ai-guardrails/hooks/")
        _would("run pre-commit install")
        _would("install Claude Code PreToolUse hook")
        _would("install dangerous-command-check hook")

    # Gitignore
    print(f"\n{GREEN}Git:{NC}")
    _would("add .ai-guardrails/ to .gitignore")

    # Exception registry
    print(f"\n{GREEN}Exception registry:{NC}")
    _would("scaffold .guardrails-exceptions.toml")

    # GitHub integrations
    is_github = _is_github_project(project_dir)
    _integration_names = [
        (install_ci, "CI workflow (.github/workflows/check.yml)"),
        (install_claude_review, "Claude Code Review workflow"),
        (install_coderabbit, "CodeRabbit config (.coderabbit.yaml)"),
        (install_gemini, "Gemini Code Assist config"),
        (install_deepsource, "DeepSource config (.deepsource.toml)"),
    ]
    active = [
        name for flag, name in _integration_names if flag == "yes" or (flag == "auto" and is_github)
    ]
    if active:
        print(f"\n{GREEN}GitHub integrations:{NC}")
        for name in active:
            _would(f"install {name}")

    # Agent instructions
    print(f"\n{GREEN}Agent instructions:{NC}")
    _would("append guardrails rules to CLAUDE.md")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_init(
    *,
    project_type: str = "",
    force: bool = False,
    skip_precommit: bool = False,
    pip_audit_mode: str = "auto",
    install_ci: str = "auto",
    install_claude_review: str = "auto",
    install_coderabbit: str = "auto",
    install_gemini: str = "auto",
    install_deepsource: str = "auto",
    dry_run: bool = False,
) -> int:
    """Run the full init workflow.

    Args:
        project_type: Language type or ``"all"`` or ``""`` for auto-detect.
        force: Overwrite existing config files.
        skip_precommit: Skip pre-commit config setup.
        pip_audit_mode: ``"auto"``, ``"pip"``, ``"uv"``, or ``"none"``.
        install_ci: ``"auto"``, ``"yes"``, or ``"no"``.
        install_claude_review: ``"auto"``, ``"yes"``, or ``"no"``.
        install_coderabbit: ``"auto"``, ``"yes"``, or ``"no"``.
        install_gemini: ``"auto"``, ``"yes"``, or ``"no"``.
        install_deepsource: ``"auto"``, ``"yes"``, or ``"no"``.
        dry_run: Show what would be done without making changes.

    Returns:
        Exit code (0 for success).

    """
    project_dir = Path.cwd()

    # Resolve installation directories
    try:
        configs_dir = find_configs_dir()
        templates_dir = find_templates_dir()
        lib_dir = find_lib_dir()
    except FileNotFoundError as e:
        print(f"{RED}Error: {e}{NC}", file=sys.stderr)
        return 1

    print(f"{BLUE}AI Guardrails - Pedantic Code Enforcement{NC}")
    print()

    # Determine languages
    languages = _resolve_languages(project_type, configs_dir, project_dir)

    if dry_run:
        print(f"{YELLOW}Dry run mode: no changes will be made{NC}")
        print(f"  Languages: {languages or ['(base only)']}")
        _dry_run_report(
            project_dir,
            languages=languages,
            project_type=project_type,
            skip_precommit=skip_precommit,
            install_ci=install_ci,
            install_claude_review=install_claude_review,
            install_coderabbit=install_coderabbit,
            install_gemini=install_gemini,
            install_deepsource=install_deepsource,
        )
        return 0

    print()

    # Copy configs
    print(f"{GREEN}Copying configs...{NC}")
    _copy_base_configs(configs_dir, project_dir, force=force)

    if project_type == "all":
        for name in _ALL_LANG_CONFIGS:
            _copy_config(configs_dir / name, project_dir / name, force=force)
    else:
        _copy_language_configs(configs_dir, project_dir, languages=languages, force=force)

    # Pre-commit
    if not skip_precommit:
        _setup_precommit(
            lib_dir,
            project_dir,
            languages=languages,
            force=force,
            pip_audit_mode=pip_audit_mode,
        )

    # Gitignore
    _add_to_gitignore(project_dir)

    # Exception registry — only regenerate configs when the registry
    # already existed (user may have customized it).  A freshly scaffolded
    # template has no custom exceptions so generating is a no-op.
    registry_existed = (project_dir / ".guardrails-exceptions.toml").exists()
    _scaffold_registry(templates_dir, project_dir, force=force)
    if registry_existed or force:
        _generate_from_registry(project_dir)

    # CI / Claude Review / CodeRabbit / Gemini / DeepSource
    is_github = _is_github_project(project_dir)

    _github_integrations: list[tuple[str, typing.Callable[[Path, Path], None]]] = [
        (install_ci, lambda t, p: _install_ci_workflow(t, p, force=force)),
        (install_claude_review, lambda t, p: _install_claude_review(t, p, force=force)),
        (install_coderabbit, lambda t, p: _install_coderabbit(t, p, force=force)),
        (install_gemini, lambda t, p: _install_gemini(t, p, force=force)),
        (install_deepsource, lambda t, p: _install_deepsource(t, p, force=force)),
    ]
    for flag, installer in _github_integrations:
        if flag == "yes" or (flag == "auto" and is_github):
            installer(templates_dir, project_dir)

    # Agent instructions
    _setup_agent_instructions(templates_dir, project_dir)

    # Done
    print()
    print(f"{GREEN}Pedantic code enforcement initialized!{NC}")
    print()
    print("Configs installed enforce:")
    print("  \u2022 Consistent formatting (EditorConfig + language formatters)")
    print("  \u2022 Required type annotations")
    print("  \u2022 Required documentation (docstrings, XML comments)")
    print("  \u2022 Strict static analysis (warnings as errors)")
    print()
    print("Run pre-commit on all files:")
    print("  pre-commit run --all-files")

    return 0


def _resolve_languages(project_type: str, configs_dir: Path, project_dir: Path) -> list[str]:
    """Determine which languages to configure."""
    if project_type == "all":
        return list(_LANG_CONFIGS.keys())

    if project_type:
        print(f"{BLUE}Detected project type:{NC} {project_type}")
        return [project_type]

    # Auto-detect via assemble module
    try:
        from guardrails.assemble import detect_languages, load_registry

        registry_path = configs_dir / "languages.yaml"
        if registry_path.exists():
            registry = load_registry(registry_path)
            detected = detect_languages(project_dir, registry)
            if detected:
                if len(detected) > 1:
                    print(f"{BLUE}Detected multiple languages:{NC} {' '.join(detected)}")
                else:
                    print(f"{BLUE}Detected project type:{NC} {detected[0]}")
                return detected
    except Exception:
        _log.debug("Language auto-detection failed", exc_info=True)

    print(f"{YELLOW}No language detected - installing base config only (.editorconfig){NC}")
    print(f"{YELLOW}Use --type or --all to install language-specific configs{NC}")
    return []
