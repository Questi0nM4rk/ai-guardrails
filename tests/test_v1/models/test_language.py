"""Tests for LanguageConfig model."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_guardrails.models.language import DetectionRules, LanguageConfig


def test_language_config_has_expected_fields() -> None:
    rules = DetectionRules(files=["pyproject.toml"], patterns=["*.py"], directories=[])
    lang = LanguageConfig(
        key="python",
        name="Python",
        detect=rules,
        configs=["ruff.toml"],
        hook_template="python.yaml",
    )
    assert lang.key == "python"
    assert lang.name == "Python"
    assert lang.configs == ["ruff.toml"]
    assert lang.hook_template == "python.yaml"


def test_detection_rules_has_files_patterns_directories() -> None:
    rules = DetectionRules(
        files=["Cargo.toml"],
        patterns=["*.rs"],
        directories=[],
    )
    assert rules.files == ["Cargo.toml"]
    assert rules.patterns == ["*.rs"]
    assert rules.directories == []


def test_load_all_returns_all_languages(tmp_path: Path) -> None:
    yaml_content = """\
python:
  name: "Python"
  detect:
    files:
      - pyproject.toml
    patterns:
      - "*.py"
    directories: []
  configs:
    - ruff.toml
  pre_commit_template: python.yaml

rust:
  name: "Rust"
  detect:
    files:
      - Cargo.toml
    patterns:
      - "*.rs"
    directories: []
  configs:
    - rustfmt.toml
  pre_commit_template: rust.yaml
"""
    yaml_file = tmp_path / "languages.yaml"
    yaml_file.write_text(yaml_content)
    langs = LanguageConfig.load_all(yaml_file)
    assert len(langs) == 2
    keys = {lang.key for lang in langs}
    assert keys == {"python", "rust"}


def test_load_all_maps_pre_commit_template_to_hook_template(tmp_path: Path) -> None:
    yaml_content = """\
python:
  name: "Python"
  detect:
    files: []
    patterns: ["*.py"]
    directories: []
  configs: []
  pre_commit_template: python.yaml
"""
    yaml_file = tmp_path / "languages.yaml"
    yaml_file.write_text(yaml_content)
    langs = LanguageConfig.load_all(yaml_file)
    assert langs[0].hook_template == "python.yaml"


def test_load_all_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        LanguageConfig.load_all(tmp_path / "missing.yaml")


def test_load_all_with_real_languages_yaml() -> None:
    real_yaml = Path(__file__).parent.parent.parent.parent / "configs" / "languages.yaml"
    langs = LanguageConfig.load_all(real_yaml)
    assert len(langs) >= 6
    keys = {lang.key for lang in langs}
    assert "python" in keys
    assert "rust" in keys
    assert "node" in keys
