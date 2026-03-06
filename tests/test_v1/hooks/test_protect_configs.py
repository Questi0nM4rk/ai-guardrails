"""Tests for protect_configs hook."""

from __future__ import annotations

import json

from ai_guardrails.hooks.protect_configs import check_tool_input, main

# ---------------------------------------------------------------------------
# check_tool_input — pure logic
# ---------------------------------------------------------------------------


def test_check_generated_config_with_hash_header(tmp_path):
    ruff = tmp_path / "ruff.toml"
    ruff.write_text("# ai-guardrails:hash:sha256:abc123\n[lint]\n")
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()

    result = check_tool_input(
        {"file_path": str(ruff)},
        project_dir=tmp_path,
    )
    assert result is not None
    assert "auto-generated" in result.lower() or "generated" in result.lower()


def test_check_generated_config_without_hash_header_allowed(tmp_path):
    ruff = tmp_path / "ruff.toml"
    ruff.write_text("[lint]\n")
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()

    result = check_tool_input(
        {"file_path": str(ruff)},
        project_dir=tmp_path,
    )
    assert result is None


def test_check_registry_file_always_asks(tmp_path):
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()

    result = check_tool_input(
        {"file_path": str(registry)},
        project_dir=tmp_path,
    )
    assert result is not None
    assert (
        "exception" in result.lower()
        or "registry" in result.lower()
        or "source of truth" in result.lower()
    )


def test_check_config_file_with_ignore_pattern_asks(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.ruff]\nignore = ["E501"]\n')
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()

    result = check_tool_input(
        {"file_path": str(pyproject), "new_string": 'ignore = ["E501"]'},
        project_dir=tmp_path,
    )
    assert result is not None
    assert "ignore" in result.lower() or "exception" in result.lower()


def test_check_config_file_without_ignore_pattern_allowed(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\nline-length = 100\n")
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()

    result = check_tool_input(
        {"file_path": str(pyproject), "new_string": "line-length = 100"},
        project_dir=tmp_path,
    )
    assert result is None


def test_check_no_registry_allows_everything(tmp_path):
    ruff = tmp_path / "ruff.toml"
    ruff.write_text("# ai-guardrails:hash:sha256:abc123\n[lint]\n")

    # No registry file — hook is inactive
    result = check_tool_input(
        {"file_path": str(ruff)},
        project_dir=tmp_path,
    )
    assert result is None


def test_check_empty_file_path_allowed(tmp_path):
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()

    result = check_tool_input({"file_path": ""}, project_dir=tmp_path)
    assert result is None


def test_check_unrelated_file_allowed(tmp_path):
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()
    src = tmp_path / "main.py"
    src.touch()

    result = check_tool_input({"file_path": str(src)}, project_dir=tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# main() — stdin JSON protocol
# ---------------------------------------------------------------------------


def test_main_no_stdin_returns_zero(tmp_path, monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.chdir(tmp_path)
    assert main() == 0


def test_main_invalid_json_returns_zero(tmp_path, monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("{not json}"))
    monkeypatch.chdir(tmp_path)
    assert main() == 0


def test_main_emits_ask_for_generated_config(tmp_path, monkeypatch, capsys):
    import io

    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()
    ruff = tmp_path / "ruff.toml"
    ruff.write_text("# ai-guardrails:hash:sha256:abc123\n[lint]\n")

    payload = json.dumps({"tool_input": {"file_path": str(ruff)}})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    monkeypatch.chdir(tmp_path)

    result = main()
    captured = capsys.readouterr()
    assert result == 0
    output = json.loads(captured.out)
    assert output["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_main_silent_for_clean_file(tmp_path, monkeypatch, capsys):
    import io

    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()
    src = tmp_path / "main.py"
    src.touch()

    payload = json.dumps({"tool_input": {"file_path": str(src)}})
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    monkeypatch.chdir(tmp_path)

    result = main()
    captured = capsys.readouterr()
    assert result == 0
    assert captured.out.strip() == ""
