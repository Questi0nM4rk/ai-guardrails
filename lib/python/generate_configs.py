"""Generate tool configs from .guardrails-exceptions.toml.

Orchestrates config generation by merging base templates (from ai-guardrails)
with project-specific exceptions (from .guardrails-exceptions.toml).

Usage:
    python3 generate_configs.py [project_dir] [--dry-run] [--check]
"""

from __future__ import annotations

import argparse
import filecmp
import sys
import tempfile
from pathlib import Path

from generators.allowlist import generate_allowlist
from generators.biome import generate_biome
from generators.codespell import generate_codespell
from generators.markdownlint import generate_markdownlint
from generators.pyright import generate_pyright
from generators.ruff import generate_ruff
from registry import ExceptionRegistry

REGISTRY_FILENAME = ".guardrails-exceptions.toml"

# ANSI colors (consistent with ai-guardrails bash scripts)
RED = "\033[0;31m"
GREEN = "\033[0;32m"
BOLD = "\033[1m"
NC = "\033[0m"


def _find_configs_dir() -> Path:
    """Find the ai-guardrails configs directory.

    Checks:
        1. Global installation (~/.ai-guardrails/configs/)
        2. Repo-relative (for development)

    Raises:
        FileNotFoundError: If no configs directory found.

    """
    # Check global installation
    global_configs = Path.home() / ".ai-guardrails" / "configs"
    if global_configs.exists():
        return global_configs

    # Check repo-relative (lib/python/ -> lib/ -> repo root)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    local_configs = repo_root / "configs"
    if local_configs.exists():
        return local_configs

    msg = "Could not find ai-guardrails configs directory"
    raise FileNotFoundError(msg)


def _find_base(name: str, local_configs: Path, global_configs: Path) -> Path | None:
    """Find a base template, preferring project-local over global."""
    for d in [local_configs, global_configs]:
        p = d / name
        if p.exists():
            return p
    return None


def _generate_to_dir(
    registry: ExceptionRegistry,
    project_path: Path,
    output_dir: Path,
) -> list[str]:
    """Generate all configs into output_dir.

    Returns:
        List of generated filenames.

    """
    local_configs = project_path / "configs"
    try:
        global_configs = _find_configs_dir()
    except FileNotFoundError:
        global_configs = Path("/nonexistent")

    generated: list[str] = []

    base_ruff = _find_base("ruff.toml", local_configs, global_configs)
    if base_ruff:
        generate_ruff(registry, base_ruff, output_dir / "ruff.toml")
        generated.append("ruff.toml")

    base_biome = _find_base("biome.json", local_configs, global_configs)
    if base_biome:
        generate_biome(registry, base_biome, output_dir / "biome.json")
        generated.append("biome.json")

    base_mdlint = _find_base(".markdownlint.jsonc", local_configs, global_configs)
    if base_mdlint:
        generate_markdownlint(registry, base_mdlint, output_dir / ".markdownlint.jsonc")
        generated.append(".markdownlint.jsonc")

    if registry.global_rules.get("codespell"):
        generate_codespell(registry, output_dir / ".codespellrc")
        generated.append(".codespellrc")

    if registry.inline_suppressions:
        generate_allowlist(registry, output_dir / ".suppression-allowlist")
        generated.append(".suppression-allowlist")

    return generated


def _check_freshness(registry: ExceptionRegistry, project_path: Path) -> bool:
    """Compare generated configs against existing files on disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        generated = _generate_to_dir(registry, project_path, tmp)

        stale: list[str] = []
        missing: list[str] = []

        for name in generated:
            actual = project_path / name
            expected = tmp / name

            if not actual.exists():
                missing.append(name)
            elif not filecmp.cmp(actual, expected, shallow=False):
                stale.append(name)

        if not stale and not missing:
            print(f"{GREEN}All generated configs are up to date.{NC}")
            return True

        if missing:
            print(f"{RED}Missing generated configs:{NC}", file=sys.stderr)
            for name in missing:
                print(f"  - {name}", file=sys.stderr)
        if stale:
            print(f"{RED}Stale generated configs (out of sync with registry):{NC}", file=sys.stderr)
            for name in stale:
                print(f"  - {name}", file=sys.stderr)

        print(f"\nRun {BOLD}ai-guardrails-generate{NC} to regenerate.", file=sys.stderr)
        return False


def run_generate_configs(
    project_dir: str = ".",
    dry_run: bool = False,
    check: bool = False,
) -> bool:
    """Generate tool configs from the exception registry.

    Args:
        project_dir: Path to project root.
        dry_run: If True, validate only, don't write files.
        check: If True, generate to temp and compare against existing files.

    Returns:
        True if generation succeeded (or check passed).

    """
    project_path = Path(project_dir).resolve()
    registry_path = project_path / REGISTRY_FILENAME

    if not registry_path.exists():
        print(f"{RED}Error: {REGISTRY_FILENAME} not found in {project_path}{NC}", file=sys.stderr)
        print("Run 'ai-guardrails-init' to scaffold one.", file=sys.stderr)
        return False

    # Load and validate
    try:
        registry = ExceptionRegistry.load(registry_path)
    except ValueError as e:
        print(f"{RED}Error loading {REGISTRY_FILENAME}: {e}{NC}", file=sys.stderr)
        return False
    errors = registry.validate()
    if errors:
        print(f"{RED}Validation errors in {REGISTRY_FILENAME}:{NC}", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return False

    if dry_run:
        print(f"{GREEN}Registry is valid.{NC}")
        return True

    if check:
        return _check_freshness(registry, project_path)

    # Generate in-place
    generated = _generate_to_dir(registry, project_path, project_path)
    for name in generated:
        print(f"  {GREEN}\u2713{NC} {name}")

    # Merge pyright into pyproject.toml (in-place only, not checkable)
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists() and registry.global_rules.get("pyright"):
        generate_pyright(registry, pyproject)
        print(f"  {GREEN}\u2713{NC} pyproject.toml [tool.pyright]")

    print(f"\n{BOLD}{GREEN}Configs generated from {REGISTRY_FILENAME}{NC}")
    return True


def main(args: list[str] | None = None) -> int:
    """CLI entry point for ai-guardrails-generate."""
    parser = argparse.ArgumentParser(
        description="Generate tool configs from .guardrails-exceptions.toml",
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="Project directory (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate registry only, don't write files",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if generated configs are up to date (exit 1 if stale)",
    )

    parsed = parser.parse_args(args)
    success = run_generate_configs(
        project_dir=parsed.project_dir,
        dry_run=parsed.dry_run,
        check=parsed.check,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
