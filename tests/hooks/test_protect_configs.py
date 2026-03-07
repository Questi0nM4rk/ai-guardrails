"""Tests for protect_configs hook."""

from __future__ import annotations

import io
import json

from ai_guardrails.generators.base import make_hash_header
from ai_guardrails.hooks.protect_configs import (
    _run_precommit,
    check_tool_input,
    main,
)

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
# main() — stdin JSON protocol (PreToolUse mode)
# ---------------------------------------------------------------------------


def test_main_no_stdin_returns_zero(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["protect-configs"])
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.chdir(tmp_path)
    assert main() == 0


def test_main_invalid_json_returns_zero(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["protect-configs"])
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json}"))
    monkeypatch.chdir(tmp_path)
    assert main() == 0


def test_main_emits_ask_for_generated_config(tmp_path, monkeypatch, capsys):
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()
    ruff = tmp_path / "ruff.toml"
    ruff.write_text("# ai-guardrails:hash:sha256:abc123\n[lint]\n")

    payload = json.dumps({"tool_input": {"file_path": str(ruff)}})
    monkeypatch.setattr("sys.argv", ["protect-configs"])
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    monkeypatch.chdir(tmp_path)

    result = main()
    captured = capsys.readouterr()
    assert result == 0
    output = json.loads(captured.out)
    assert output["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_main_silent_for_clean_file(tmp_path, monkeypatch, capsys):
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()
    src = tmp_path / "main.py"
    src.touch()

    payload = json.dumps({"tool_input": {"file_path": str(src)}})
    monkeypatch.setattr("sys.argv", ["protect-configs"])
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    monkeypatch.chdir(tmp_path)

    result = main()
    captured = capsys.readouterr()
    assert result == 0
    assert captured.out.strip() == ""


# ---------------------------------------------------------------------------
# _run_precommit — pre-commit / lefthook mode
# ---------------------------------------------------------------------------


def test_precommit_mode_detects_tampered_file(tmp_path, capsys):
    """File with hash header whose hash does not match body returns 1."""
    body = "[lint]\nselect = ['ALL']\n"
    # Write a valid-looking header but with a wrong hash
    tampered = "# ai-guardrails:hash:sha256:0000dead0000beef\n" + body
    ruff = tmp_path / "ruff.toml"
    ruff.write_text(tampered)

    result = _run_precommit([str(ruff)])
    assert result == 1

    captured = capsys.readouterr()
    assert "tampered" in captured.out.lower() or "hash mismatch" in captured.out.lower()


def test_precommit_mode_passes_clean_file(tmp_path):
    """File with valid hash header matching body returns 0."""
    body = "[lint]\nselect = ['ALL']\n"
    header = make_hash_header(body)
    ruff = tmp_path / "ruff.toml"
    ruff.write_text(f"{header}\n{body}")

    result = _run_precommit([str(ruff)])
    assert result == 0


def test_precommit_mode_ignores_non_generated_config(tmp_path):
    """File not in GENERATED_CONFIGS is skipped, returns 0."""
    unrelated = tmp_path / "myapp.toml"
    unrelated.write_text("# ai-guardrails:hash:sha256:badhash\ncontent\n")

    result = _run_precommit([str(unrelated)])
    assert result == 0


def test_precommit_mode_ignores_file_without_hash_header(tmp_path):
    """Generated config name but no hash header is skipped, returns 0."""
    ruff = tmp_path / "ruff.toml"
    ruff.write_text("[lint]\nselect = ['ALL']\n")

    result = _run_precommit([str(ruff)])
    assert result == 0


def test_main_dispatches_to_precommit_with_argv(tmp_path, monkeypatch, capsys):
    """When sys.argv has filenames, main() delegates to _run_precommit."""
    body = "[lint]\n"
    tampered = "# ai-guardrails:hash:sha256:badhash\n" + body
    ruff = tmp_path / "ruff.toml"
    ruff.write_text(tampered)

    monkeypatch.setattr("sys.argv", ["protect-configs", str(ruff)])
    monkeypatch.setattr("sys.stdin", io.StringIO(""))

    result = main()
    assert result == 1

    captured = capsys.readouterr()
    assert "tampered" in captured.out.lower() or "hash mismatch" in captured.out.lower()


def test_main_dispatches_to_pretool_with_stdin(tmp_path, monkeypatch, capsys):
    """When sys.argv has no files but stdin has JSON, PreToolUse logic runs."""
    registry = tmp_path / ".guardrails-exceptions.toml"
    registry.touch()
    ruff = tmp_path / "ruff.toml"
    ruff.write_text("# ai-guardrails:hash:sha256:abc123\n[lint]\n")

    payload = json.dumps({"tool_input": {"file_path": str(ruff)}})
    monkeypatch.setattr("sys.argv", ["protect-configs"])
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    monkeypatch.chdir(tmp_path)

    result = main()
    captured = capsys.readouterr()
    assert result == 0
    output = json.loads(captured.out)
    assert output["hookSpecificOutput"]["permissionDecision"] == "ask"
