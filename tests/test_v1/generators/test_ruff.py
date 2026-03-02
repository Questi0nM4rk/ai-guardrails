"""Tests for RuffGenerator — merges base ruff.toml with registry exceptions."""

from __future__ import annotations

import tomllib  # type: ignore[no-redef]
from pathlib import Path

import pytest
import tomli_w

from ai_guardrails.generators.ruff import RuffGenerator
from ai_guardrails.models.registry import ExceptionRegistry


def _make_registry(
    ignore_rules: list[str] | None = None,
    file_exceptions: list[dict] | None = None,  # type: ignore[type-arg]
    custom: dict | None = None,  # type: ignore[type-arg]
) -> ExceptionRegistry:
    global_rules = {}
    if ignore_rules:
        global_rules["ruff"] = {"ignore": ignore_rules}
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": global_rules,
            "exceptions": [],
            "file_exceptions": file_exceptions or [],
            "custom": custom or {},
            "inline_suppressions": [],
        }
    )


def _write_base_toml(path: Path, content: dict) -> None:  # type: ignore[type-arg]
    with path.open("wb") as f:
        tomli_w.dump(content, f)


BASE_CONFIG = {
    "target-version": "py311",
    "line-length": 88,
    "lint": {
        "select": ["ALL"],
        "ignore": ["W191", "E111", "COM812"],
        "per-file-ignores": {
            "tests/**/*.py": ["ARG001", "PLR2004"],
        },
    },
}


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    _write_base_toml(configs_dir / "ruff.toml", BASE_CONFIG)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    return configs_dir, project_dir


def test_ruff_generator_name(tmp_path: Path) -> None:
    gen = RuffGenerator(configs_dir=tmp_path)
    assert gen.name == "ruff"


def test_ruff_generator_output_files(tmp_path: Path) -> None:
    gen = RuffGenerator(configs_dir=tmp_path)
    assert gen.output_files == ["ruff.toml"]


def test_generate_output_has_hash_header(tmp_path: Path) -> None:
    configs_dir, project_dir = _setup(tmp_path)
    gen = RuffGenerator(configs_dir=configs_dir)
    result = gen.generate(_make_registry(), ["python"], project_dir)
    content = result[project_dir / "ruff.toml"]
    assert content.startswith("# ai-guardrails:hash:sha256:")


def test_generate_preserves_base_config_values(tmp_path: Path) -> None:
    configs_dir, project_dir = _setup(tmp_path)
    gen = RuffGenerator(configs_dir=configs_dir)
    result = gen.generate(_make_registry(), ["python"], project_dir)
    content = result[project_dir / "ruff.toml"]

    # Strip the hash header line and parse TOML from the rest
    body = content.split("\n", 1)[1]
    parsed = tomllib.loads(body)
    assert parsed["target-version"] == "py311"
    assert parsed["line-length"] == 88


def test_generate_merges_global_ignores(tmp_path: Path) -> None:
    configs_dir, project_dir = _setup(tmp_path)
    gen = RuffGenerator(configs_dir=configs_dir)
    registry = _make_registry(ignore_rules=["E501", "W503"])
    result = gen.generate(registry, ["python"], project_dir)
    content = result[project_dir / "ruff.toml"]

    body = content.split("\n", 1)[1]
    parsed = tomllib.loads(body)
    ignores = parsed["lint"]["ignore"]
    # Should be union of base ignores and registry ignores
    assert "W191" in ignores  # from base
    assert "COM812" in ignores  # from base
    assert "E501" in ignores  # from registry
    assert "W503" in ignores  # from registry


def test_generate_ignores_are_sorted(tmp_path: Path) -> None:
    configs_dir, project_dir = _setup(tmp_path)
    gen = RuffGenerator(configs_dir=configs_dir)
    registry = _make_registry(ignore_rules=["Z999", "A001"])
    result = gen.generate(registry, ["python"], project_dir)
    content = result[project_dir / "ruff.toml"]

    body = content.split("\n", 1)[1]
    parsed = tomllib.loads(body)
    ignores = parsed["lint"]["ignore"]
    assert ignores == sorted(ignores)


def test_generate_merges_per_file_ignores(tmp_path: Path) -> None:
    configs_dir, project_dir = _setup(tmp_path)
    gen = RuffGenerator(configs_dir=configs_dir)
    registry = _make_registry(
        file_exceptions=[
            {
                "glob": "tests/**/*.py",
                "tool": "ruff",
                "rules": ["S101", "SLF001"],
                "reason": "Test files",
            }
        ]
    )
    result = gen.generate(registry, ["python"], project_dir)
    content = result[project_dir / "ruff.toml"]

    body = content.split("\n", 1)[1]
    parsed = tomllib.loads(body)
    per_file = parsed["lint"]["per-file-ignores"]["tests/**/*.py"]
    # Should be union of base rules and registry rules
    assert "ARG001" in per_file  # from base
    assert "PLR2004" in per_file  # from base
    assert "S101" in per_file  # from registry
    assert "SLF001" in per_file  # from registry


def test_generate_adds_new_glob_per_file_ignores(tmp_path: Path) -> None:
    configs_dir, project_dir = _setup(tmp_path)
    gen = RuffGenerator(configs_dir=configs_dir)
    registry = _make_registry(
        file_exceptions=[
            {
                "glob": "src/cli.py",
                "tool": "ruff",
                "rules": ["T201"],
                "reason": "Print in CLI",
            }
        ]
    )
    result = gen.generate(registry, ["python"], project_dir)
    content = result[project_dir / "ruff.toml"]

    body = content.split("\n", 1)[1]
    parsed = tomllib.loads(body)
    assert "src/cli.py" in parsed["lint"]["per-file-ignores"]
    assert "T201" in parsed["lint"]["per-file-ignores"]["src/cli.py"]


def test_generate_ignores_non_ruff_file_exceptions(tmp_path: Path) -> None:
    configs_dir, project_dir = _setup(tmp_path)
    gen = RuffGenerator(configs_dir=configs_dir)
    registry = _make_registry(
        file_exceptions=[
            {
                "glob": "src/cli.py",
                "tool": "markdownlint",
                "rules": ["MD001"],
                "reason": "other tool",
            }
        ]
    )
    result = gen.generate(registry, ["python"], project_dir)
    content = result[project_dir / "ruff.toml"]

    body = content.split("\n", 1)[1]
    parsed = tomllib.loads(body)
    assert "src/cli.py" not in parsed["lint"].get("per-file-ignores", {})


def test_generate_raises_if_base_missing(tmp_path: Path) -> None:
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    gen = RuffGenerator(configs_dir=configs_dir)
    with pytest.raises(FileNotFoundError):
        gen.generate(_make_registry(), ["python"], project_dir)


def test_check_returns_empty_when_fresh(tmp_path: Path) -> None:
    configs_dir, project_dir = _setup(tmp_path)
    gen = RuffGenerator(configs_dir=configs_dir)
    registry = _make_registry(ignore_rules=["E501"])

    generated = gen.generate(registry, ["python"], project_dir)
    for path, content in generated.items():
        path.write_text(content)

    assert gen.check(registry, project_dir) == []


def test_check_returns_issue_when_missing(tmp_path: Path) -> None:
    configs_dir, project_dir = _setup(tmp_path)
    gen = RuffGenerator(configs_dir=configs_dir)

    issues = gen.check(_make_registry(), project_dir)
    assert len(issues) == 1
    assert "ruff.toml" in issues[0]


def test_check_returns_issue_when_stale(tmp_path: Path) -> None:
    configs_dir, project_dir = _setup(tmp_path)
    gen = RuffGenerator(configs_dir=configs_dir)

    # Generate with empty registry
    generated = gen.generate(_make_registry(), ["python"], project_dir)
    for path, content in generated.items():
        path.write_text(content)

    # Check with different registry
    registry_v2 = _make_registry(ignore_rules=["E501"])
    issues = gen.check(registry_v2, project_dir)
    assert len(issues) == 1
    assert "ruff.toml" in issues[0]
