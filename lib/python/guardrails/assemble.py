"""Assemble pre-commit config from modular templates.

This script reads the language registry, detects languages present in a project,
and merges the appropriate templates into a single .pre-commit-config.yaml file.

Usage:
    python -m guardrails.assemble --project-dir /path/to/project
    python -m guardrails.assemble --languages python go
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


def load_registry(registry_path: Path) -> dict[str, Any]:
    """Load language registry from YAML file.

    Args:
        registry_path: Path to languages.yaml

    Returns:
        Dictionary of language configurations

    Raises:
        FileNotFoundError: If registry file doesn't exist
        yaml.YAMLError: If registry file is invalid YAML
        TypeError: If registry is not a dict

    """
    with registry_path.open() as f:
        result = yaml.safe_load(f)
    if not isinstance(result, dict):
        msg = f"Registry must be a dict, got {type(result).__name__}"
        raise TypeError(msg)
    return result


def detect_languages(project_dir: Path, registry: dict[str, Any]) -> list[str]:
    """Detect languages present in project based on registry rules.

    Detection rules are evaluated in order:
    1. Check for specific files (exact match)
    2. Check for file patterns (glob match)
    3. Check for directories

    Args:
        project_dir: Path to project directory
        registry: Language registry from languages.yaml

    Returns:
        List of detected language keys (e.g., ["python", "go"])

    """
    detected: list[str] = []

    for lang, config in registry.items():
        rules = config.get("detect", {})

        # Check for specific files
        files = rules.get("files", [])
        if any((project_dir / f).exists() for f in files):
            detected.append(lang)
            continue

        # Check for file patterns (recursive search)
        patterns = rules.get("patterns", [])
        for pattern in patterns:
            # Use ** prefix for recursive search (e.g., src/main.py)
            recursive_pattern = f"**/{pattern}"
            if list(project_dir.glob(recursive_pattern)):
                detected.append(lang)
                break
        else:
            # Check for directories
            directories = rules.get("directories", [])
            if any((project_dir / d).is_dir() for d in directories):
                detected.append(lang)

    return detected


def load_template(template_path: Path) -> dict[str, Any]:
    """Load a pre-commit template YAML file.

    Args:
        template_path: Path to template file

    Returns:
        Parsed YAML dictionary

    Raises:
        FileNotFoundError: If template doesn't exist
        yaml.YAMLError: If template is invalid YAML
        TypeError: If template is not a dict

    """
    with template_path.open() as f:
        result = yaml.safe_load(f)
    if not isinstance(result, dict):
        msg = f"Template must be a dict, got {type(result).__name__}"
        raise TypeError(msg)
    return result


def assemble_config(
    languages: list[str],
    registry: dict[str, Any],
    templates_dir: Path,
) -> dict[str, Any]:
    """Merge base + detected language templates.

    Args:
        languages: List of detected language keys
        registry: Language registry
        templates_dir: Path to templates/pre-commit/ directory

    Returns:
        Merged pre-commit configuration dictionary

    """
    # Always start with base template
    base_path = templates_dir / "base.yaml"
    config = load_template(base_path)

    # Ensure config has "repos" key (initialize empty list if missing)
    if "repos" not in config:
        config["repos"] = []

    # Merge each detected language's template
    for lang in languages:
        lang_config = registry.get(lang, {})
        template_name = lang_config.get("pre_commit_template")

        if not template_name:
            continue

        template_path = templates_dir / template_name
        if not template_path.exists():
            print(f"Warning: Template {template_name} not found", file=sys.stderr)
            continue

        lang_template = load_template(template_path)
        # Handle lang_template.get("repos") being None by treating as empty list
        repos = lang_template.get("repos") or []
        config["repos"].extend(repos)

    return config


class MultilineDumper(yaml.SafeDumper):
    """Custom YAML dumper that uses block style for multiline strings."""


def _str_representer(dumper: MultilineDumper, data: str) -> yaml.Node:
    """Represent multiline strings with block style."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


MultilineDumper.add_representer(str, _str_representer)


def write_config(config: dict[str, Any], output_path: Path) -> None:
    """Write assembled config to file.

    Args:
        config: Assembled pre-commit configuration
        output_path: Path to write .pre-commit-config.yaml

    """
    with output_path.open("w") as f:
        # Write header comment
        f.write("# =============================================================================\n")
        f.write("# AI Guardrails - Auto-Generated Pre-Commit Configuration\n")
        f.write("# =============================================================================\n")
        f.write("# Generated by: python -m guardrails.assemble\n")
        f.write("# Do not edit manually - regenerate with ai-guardrails init\n")
        f.write(
            "# =============================================================================\n\n"
        )
        yaml.dump(
            config,
            f,
            Dumper=MultilineDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def find_installation_paths() -> tuple[Path, Path]:
    """Find configs and templates directories.

    Checks:
    1. Global installation at ~/.ai-guardrails/
    2. Local development paths relative to this script

    Returns:
        Tuple of (configs_dir, templates_dir)

    Raises:
        FileNotFoundError: If installation directories not found

    """
    # Check global installation first
    global_install = Path.home() / ".ai-guardrails"
    if (global_install / "configs" / "languages.yaml").exists():
        return global_install / "configs", global_install / "templates" / "pre-commit"

    # Check local development paths
    # guardrails/assemble.py -> guardrails -> python -> lib -> repo root
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent.parent

    configs_dir = repo_root / "configs"
    templates_dir = repo_root / "templates" / "pre-commit"

    if (configs_dir / "languages.yaml").exists():
        return configs_dir, templates_dir

    msg = "Could not find AI Guardrails installation"
    raise FileNotFoundError(msg)


def main(args: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, 1 for failure)

    """
    parser = argparse.ArgumentParser(
        description="Assemble pre-commit config from modular templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect languages in current directory
  python -m guardrails.assemble

  # Auto-detect in specific directory
  python -m guardrails.assemble --project-dir /path/to/project

  # Specify languages explicitly
  python -m guardrails.assemble --languages python go

  # Output to custom path
  python -m guardrails.assemble --output /tmp/test.yaml
        """,
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project directory to detect languages in (default: current directory)",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        help="Languages to include (skip auto-detection)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path (default: PROJECT_DIR/.pre-commit-config.yaml)",
    )
    parser.add_argument(
        "--list-detected",
        action="store_true",
        help="Only list detected languages, don't generate config",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print config to stdout instead of writing file",
    )

    parsed = parser.parse_args(args)

    # Find installation paths
    try:
        configs_dir, templates_dir = find_installation_paths()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Load registry
    registry_path = configs_dir / "languages.yaml"
    try:
        registry = load_registry(registry_path)
    except FileNotFoundError:
        print(f"Error: Registry not found at {registry_path}", file=sys.stderr)
        return 1
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in registry: {e}", file=sys.stderr)
        return 1
    except TypeError as e:
        print(f"Error: Invalid registry format: {e}", file=sys.stderr)
        return 1

    # Detect or use specified languages
    if parsed.languages:
        languages = parsed.languages
        # Validate languages exist in registry
        invalid = [lang for lang in languages if lang not in registry]
        if invalid:
            print(f"Error: Unknown languages: {', '.join(invalid)}", file=sys.stderr)
            print(f"Valid languages: {', '.join(registry.keys())}", file=sys.stderr)
            return 1
    else:
        languages = detect_languages(parsed.project_dir, registry)

    # Handle --list-detected
    if parsed.list_detected:
        # Output nothing if no languages detected (for bash parsing)
        for lang in languages:
            config = registry[lang]
            print(f"{lang}: {config.get('name', lang)}")
        return 0

    # Assemble config
    if not languages:
        print("Warning: No languages detected, using base config only", file=sys.stderr)

    try:
        config = assemble_config(languages, registry, templates_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except TypeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in template: {e}", file=sys.stderr)
        return 1

    # Output
    if parsed.dry_run:
        yaml.dump(
            config,
            sys.stdout,
            Dumper=MultilineDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
        return 0

    output_path = parsed.output or (parsed.project_dir / ".pre-commit-config.yaml")
    write_config(config, output_path)

    # Report what was done
    if languages:
        lang_names = [registry[lang].get("name", lang) for lang in languages]
        print(f"Generated {output_path} for: {', '.join(lang_names)}")
    else:
        print(f"Generated {output_path} (base config only)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
