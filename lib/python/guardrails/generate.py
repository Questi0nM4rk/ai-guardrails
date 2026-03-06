"""Generate tool configs from .guardrails-exceptions.toml.

Orchestrates config generation by merging base templates (from ai-guardrails)
with project-specific exceptions (from .guardrails-exceptions.toml).

Usage:
    python3 -m guardrails.generate [project_dir] [--dry-run] [--check]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

import yaml

from guardrails._paths import find_base_config, find_configs_dir
from guardrails.assemble import detect_languages as _detect_project_languages
from guardrails.assemble import load_registry as _load_lang_registry
from guardrails.constants import BOLD, GREEN, NC, RED, REGISTRY_FILENAME
from guardrails.generators.allowlist import generate_allowlist
from guardrails.generators.biome import generate_biome
from guardrails.generators.codespell import generate_codespell
from guardrails.generators.markdownlint import generate_markdownlint
from guardrails.generators.pyright import generate_pyright
from guardrails.generators.ruff import generate_ruff
from guardrails.registry import ExceptionRegistry


def _lang_config_set(languages: list[str] | None) -> set[str] | None:
    """Return config filenames relevant to detected languages, or None for all.

    Args:
        languages: Detected language keys, or None to generate everything.

    Returns:
        Set of config filenames (e.g. {"ruff.toml"}), or None if all should
        be generated.

    """
    if languages is None:
        return None
    try:
        configs_dir = find_configs_dir()
        lang_yaml_path = configs_dir / "languages.yaml"
        with lang_yaml_path.open() as f:
            lang_registry: dict[str, dict[str, list[str]]] = yaml.safe_load(f)
    except (FileNotFoundError, yaml.YAMLError):
        # If we can't load languages.yaml, fall back to generating everything
        return None
    result: set[str] = set()
    for lang in languages:
        if lang in lang_registry:
            for cfg in lang_registry[lang].get("configs", []):
                result.add(cfg)
    return result


def _detect_languages_for_project(project_path: Path) -> list[str] | None:
    """Detect languages in a project using assemble.detect_languages.

    Returns:
        List of detected language keys, or None if detection fails.

    """
    try:
        configs_dir = find_configs_dir()
        lang_registry = _load_lang_registry(configs_dir / "languages.yaml")
        return _detect_project_languages(project_path, lang_registry)
    except (FileNotFoundError, yaml.YAMLError, TypeError):
        return None


def _generate_to_dir(
    registry: ExceptionRegistry,
    project_path: Path,
    output_dir: Path,
    languages: list[str] | None = None,
) -> list[str]:
    """Generate configs into output_dir, filtered by detected languages.

    Args:
        registry: Parsed exception registry.
        project_path: Path to the consumer project.
        output_dir: Directory to write generated configs into.
        languages: Detected language keys. If None, all configs are generated
            (backward-compatible default).

    Returns:
        List of generated filenames.

    """
    generated: list[str] = []
    lang_configs = _lang_config_set(languages)

    # Language-specific generators: only run if the language is detected
    base_ruff = find_base_config("ruff.toml", project_path)
    if base_ruff and (lang_configs is None or "ruff.toml" in lang_configs):
        generate_ruff(registry, base_ruff, output_dir / "ruff.toml")
        generated.append("ruff.toml")

    base_biome = find_base_config("biome.json", project_path)
    if base_biome and (lang_configs is None or "biome.json" in lang_configs):
        generate_biome(registry, base_biome, output_dir / "biome.json")
        generated.append("biome.json")

    # Language-agnostic generators: always run
    base_mdlint = find_base_config(".markdownlint.jsonc", project_path)
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


def _semantically_equal(actual: Path, expected: Path) -> bool:
    """Compare two config files semantically, ignoring formatting differences."""
    suffix = actual.suffix
    try:
        if suffix == ".toml":
            with actual.open("rb") as f:
                a = tomllib.load(f)
            with expected.open("rb") as f:
                e = tomllib.load(f)
            return a == e
        if suffix in {".json", ".jsonc"}:
            a = json.loads(actual.read_text())
            e = json.loads(expected.read_text())
            return a == e
    except (tomllib.TOMLDecodeError, json.JSONDecodeError, OSError):
        # Parsing failed -- fall through to byte comparison
        pass
    # Fallback: byte comparison for unknown formats
    return actual.read_bytes() == expected.read_bytes()


def _check_freshness(registry: ExceptionRegistry, project_path: Path) -> bool:
    """Compare generated configs against existing files on disk."""
    languages = _detect_languages_for_project(project_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        generated = _generate_to_dir(registry, project_path, tmp, languages=languages)

        stale: list[str] = []
        missing: list[str] = []

        for name in generated:
            actual = project_path / name
            expected = tmp / name

            if not actual.exists():
                missing.append(name)
            elif not _semantically_equal(actual, expected):
                stale.append(name)

        if not stale and not missing:
            print(f"{GREEN}All generated configs are up to date.{NC}")
            return True

        if missing:
            print(f"{RED}Missing generated configs:{NC}", file=sys.stderr)
            for name in missing:
                print(f"  - {name}", file=sys.stderr)
        if stale:
            print(
                f"{RED}Stale generated configs (out of sync with registry):{NC}",
                file=sys.stderr,
            )
            for name in stale:
                print(f"  - {name}", file=sys.stderr)

        print(f"\nRun {BOLD}ai-guardrails-generate{NC} to regenerate.", file=sys.stderr)
        return False


def _load_registry(project_path: Path) -> ExceptionRegistry | None:
    """Load and validate the exception registry, printing errors on failure."""
    registry_path = project_path / REGISTRY_FILENAME

    if not registry_path.exists():
        print(
            f"{RED}Error: {REGISTRY_FILENAME} not found in {project_path}{NC}",
            file=sys.stderr,
        )
        print("Run 'ai-guardrails-init' to scaffold one.", file=sys.stderr)
        return None

    try:
        registry = ExceptionRegistry.load(registry_path)
    except ValueError as e:
        print(f"{RED}Error loading {REGISTRY_FILENAME}: {e}{NC}", file=sys.stderr)
        return None

    errors = registry.validate()
    if errors:
        print(f"{RED}Validation errors in {REGISTRY_FILENAME}:{NC}", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return None

    return registry


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
    registry = _load_registry(project_path)
    if registry is None:
        return False

    if dry_run:
        print(f"{GREEN}Registry is valid.{NC}")
        return True

    if check:
        return _check_freshness(registry, project_path)

    # Detect languages to filter generation
    languages = _detect_languages_for_project(project_path)

    # Generate atomically: write to tempdir, then move on success
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        try:
            generated = _generate_to_dir(
                registry, project_path, tmp, languages=languages
            )
        except Exception as e:  # noqa: BLE001
            print(f"{RED}Error during config generation: {e}{NC}", file=sys.stderr)
            return False
        for name in generated:
            shutil.move(str(tmp / name), str(project_path / name))
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
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate registry only, don't write files",
    )
    mode_group.add_argument(
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
