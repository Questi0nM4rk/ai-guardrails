"""Tests for ConfigLoader infrastructure."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from ai_guardrails.infra.config_loader import ConfigLoader, deep_merge

# ---------------------------------------------------------------------------
# TOML loading
# ---------------------------------------------------------------------------


def test_load_toml_returns_parsed_data(tmp_path: Path) -> None:
    loader = ConfigLoader()
    toml_file = tmp_path / "config.toml"
    toml_file.write_text('[section]\nkey = "value"\n')
    result = loader.load_toml(toml_file)
    assert result["section"]["key"] == "value"


def test_load_toml_missing_file_raises(tmp_path: Path) -> None:
    loader = ConfigLoader()
    with pytest.raises(FileNotFoundError):
        loader.load_toml(tmp_path / "missing.toml")


def test_load_toml_invalid_syntax_raises(tmp_path: Path) -> None:
    loader = ConfigLoader()
    bad = tmp_path / "bad.toml"
    bad.write_text("not = [valid toml\n")
    with pytest.raises(tomllib.TOMLDecodeError):
        loader.load_toml(bad)


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def test_load_yaml_returns_parsed_data(tmp_path: Path) -> None:
    loader = ConfigLoader()
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("key: value\nnested:\n  a: 1\n")
    result = loader.load_yaml(yaml_file)
    assert result["key"] == "value"
    assert result["nested"]["a"] == 1


def test_load_yaml_missing_file_raises(tmp_path: Path) -> None:
    loader = ConfigLoader()
    with pytest.raises(FileNotFoundError):
        loader.load_yaml(tmp_path / "missing.yaml")


# ---------------------------------------------------------------------------
# JSON loading
# ---------------------------------------------------------------------------


def test_load_json_returns_parsed_data(tmp_path: Path) -> None:
    loader = ConfigLoader()
    json_file = tmp_path / "config.json"
    json_file.write_text('{"key": "value", "num": 42}')
    result = loader.load_json(json_file)
    assert result["key"] == "value"
    assert result["num"] == 42


def test_load_json_missing_file_raises(tmp_path: Path) -> None:
    loader = ConfigLoader()
    with pytest.raises(FileNotFoundError):
        loader.load_json(tmp_path / "missing.json")


def test_load_json_invalid_raises(tmp_path: Path) -> None:
    loader = ConfigLoader()
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    with pytest.raises(json.JSONDecodeError):
        loader.load_json(bad)


# ---------------------------------------------------------------------------
# deep_merge
# ---------------------------------------------------------------------------


def test_deep_merge_base_only_returns_base() -> None:
    result = deep_merge({"a": 1}, {})
    assert result == {"a": 1}


def test_deep_merge_override_only_adds_keys() -> None:
    result = deep_merge({}, {"b": 2})
    assert result == {"b": 2}


def test_deep_merge_override_replaces_scalar() -> None:
    result = deep_merge({"a": 1}, {"a": 99})
    assert result["a"] == 99


def test_deep_merge_nested_dicts_are_merged_recursively() -> None:
    base = {"section": {"a": 1, "b": 2}}
    override = {"section": {"b": 99, "c": 3}}
    result = deep_merge(base, override)
    assert result["section"] == {"a": 1, "b": 99, "c": 3}


def test_deep_merge_does_not_mutate_base() -> None:
    base = {"a": {"x": 1}}
    override = {"a": {"y": 2}}
    deep_merge(base, override)
    assert base == {"a": {"x": 1}}


def test_deep_merge_override_list_replaces_base_list() -> None:
    base = {"items": [1, 2, 3]}
    override = {"items": [4, 5]}
    result = deep_merge(base, override)
    assert result["items"] == [4, 5]
