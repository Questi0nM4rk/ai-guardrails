"""Tests for guardrails.hooks.suppress_comments -- suppression comment detector."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from guardrails.hooks.suppress_comments import (
    _MAX_VIOLATIONS_PER_PATTERN,
    _infer_extension,
    _is_allowlisted,
    _is_test_file,
    _load_allowlist,
    main,
)


class TestIsTestFile:
    """Test test-file path detection."""

    def test_tests_directory(self) -> None:
        assert _is_test_file("project/tests/test_foo.py") is True

    def test_test_directory(self) -> None:
        assert _is_test_file("project/test/foo.py") is True

    def test_dunder_tests(self) -> None:
        assert _is_test_file("project/__tests__/foo.spec.ts") is True

    def test_spec_directory(self) -> None:
        assert _is_test_file("project/spec/models_spec.rb") is True

    def test_test_prefix_basename(self) -> None:
        assert _is_test_file("src/test_utils.py") is True

    def test_test_suffix_basename(self) -> None:
        assert _is_test_file("src/utils_test.go") is True

    def test_spec_suffix_basename(self) -> None:
        assert _is_test_file("src/utils.spec.ts") is True

    def test_underscore_spec_suffix(self) -> None:
        assert _is_test_file("src/utils_spec.rb") is True

    def test_non_test_file(self) -> None:
        assert _is_test_file("src/utils.py") is False

    def test_non_test_deep_path(self) -> None:
        assert _is_test_file("lib/python/guardrails/hooks/config_ignore.py") is False


class TestInferExtension:
    """Test language extension inference."""

    def test_normal_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "script.py"
        f.write_text("print('hello')\n")
        assert _infer_extension(str(f)) == "py"

    def test_ts_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "component.tsx"
        f.write_text("export default function() {}\n")
        assert _infer_extension(str(f)) == "tsx"

    def test_dotfile_bashrc(self, tmp_path: Path) -> None:
        f = tmp_path / ".bashrc"
        f.write_text("alias ll='ls -la'\n")
        assert _infer_extension(str(f)) == "bash"

    def test_dotfile_zshrc(self, tmp_path: Path) -> None:
        f = tmp_path / ".zshrc"
        f.write_text("export PATH=$PATH\n")
        assert _infer_extension(str(f)) == "bash"

    def test_dotfile_profile(self, tmp_path: Path) -> None:
        f = tmp_path / ".profile"
        f.write_text("export EDITOR=vim\n")
        assert _infer_extension(str(f)) == "sh"

    def test_shebang_bash(self, tmp_path: Path) -> None:
        f = tmp_path / "myscript"
        f.write_text("#!/usr/bin/env bash\necho hi\n")
        assert _infer_extension(str(f)) == "bash"

    def test_shebang_python(self, tmp_path: Path) -> None:
        f = tmp_path / "run"
        f.write_text("#!/usr/bin/env python3\nimport sys\n")
        assert _infer_extension(str(f)) == "py"

    def test_shebang_node(self, tmp_path: Path) -> None:
        f = tmp_path / "run"
        f.write_text("#!/usr/bin/env node\nconsole.log('hi');\n")
        assert _infer_extension(str(f)) == "js"

    def test_shebang_sh(self, tmp_path: Path) -> None:
        f = tmp_path / "run"
        f.write_text("#!/bin/sh\necho hello\n")
        assert _infer_extension(str(f)) == "sh"

    def test_no_extension_no_shebang(self, tmp_path: Path) -> None:
        f = tmp_path / "data"
        f.write_text("just some data\n")
        assert _infer_extension(str(f)) is None

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        assert _infer_extension(str(tmp_path / "missing")) is None


class TestLoadAllowlist:
    """Test suppression allowlist loading."""

    def test_load_populated(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        f = tmp_path / ".suppression-allowlist"
        f.write_text("# comment\nnoqa: BLE001\ntype: ignore\\[import\\]\n\n")
        result = _load_allowlist()
        assert len(result) == 2
        assert "noqa: BLE001" in result

    def test_load_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert _load_allowlist() == []

    def test_load_empty_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        f = tmp_path / ".suppression-allowlist"
        f.write_text("")
        assert _load_allowlist() == []

    def test_skips_comments_and_blanks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        f = tmp_path / ".suppression-allowlist"
        f.write_text("# comment\n\n  \npattern1\n")
        result = _load_allowlist()
        assert result == ["pattern1"]


class TestIsAllowlisted:
    """Test allowlist regex matching."""

    def test_match(self) -> None:
        assert _is_allowlisted("file.py:10:# noqa: BLE001", ["noqa: BLE001"]) is True

    def test_no_match(self) -> None:
        assert _is_allowlisted("file.py:10:# noqa: E501", ["noqa: BLE001"]) is False

    def test_empty_allowlist(self) -> None:
        assert _is_allowlisted("file.py:10:# noqa", []) is False

    def test_invalid_regex_skipped(self) -> None:
        """Invalid regex patterns should be skipped, not raise."""
        assert _is_allowlisted("file.py:10:# noqa", ["[invalid"]) is False

    def test_case_insensitive(self) -> None:
        assert _is_allowlisted("file.py:10:# NOQA: BLE001", ["noqa: BLE001"]) is True


class TestMain:
    """Test the main() entry point for suppression detection.

    Note: pytest tmp_path names contain "test_" which triggers _is_test_file().
    An autouse fixture mocks _is_test_file to return False so we can test
    suppression detection on files without path-based false positives.
    """

    @pytest.fixture(autouse=True)
    def _bypass_test_file_detection(self) -> Iterator[None]:
        with patch("guardrails.hooks.suppress_comments._is_test_file", return_value=False):
            yield

    def test_no_files_returns_0(self) -> None:
        assert main([]) == 0

    def test_clean_file_returns_0(self, tmp_path: Path) -> None:
        f = tmp_path / "clean.py"
        f.write_text("x = 1\ny = 2\n")
        assert main([str(f)]) == 0

    def test_noqa_in_python_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("x = 1  # noqa: E501\n")
        assert main([str(f)]) == 1

    def test_type_ignore_in_python_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("x: int = 'a'  # type: ignore\n")
        assert main([str(f)]) == 1

    def test_eslint_disable_in_ts_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.ts"
        f.write_text("// eslint-disable-next-line no-unused-vars\n")
        assert main([str(f)]) == 1

    def test_ts_ignore_in_tsx_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.tsx"
        f.write_text("// @ts-ignore\nconst x = 1;\n")
        assert main([str(f)]) == 1

    def test_nonexistent_file_skipped(self, tmp_path: Path) -> None:
        assert main([str(tmp_path / "missing.py")]) == 0

    def test_allowlisted_suppression_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        allowlist = tmp_path / ".suppression-allowlist"
        allowlist.write_text("noqa: BLE001\n")
        f = tmp_path / "ok.py"
        f.write_text("x = 1  # noqa: BLE001\n")
        assert main([str(f)]) == 0

    def test_shell_check_disable_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.sh"
        f.write_text("#!/bin/bash\n# shellcheck disable=SC2034\nx=unused\n")
        assert main([str(f)]) == 1

    def test_rust_allow_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.rs"
        f.write_text("#[allow(dead_code)]\nfn unused() {}\n")
        assert main([str(f)]) == 1

    def test_pragma_no_cover_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("if False:  # pragma: no cover\n    pass\n")
        assert main([str(f)]) == 1

    def test_output_contains_error_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "bad.py"
        f.write_text("x = 1  # noqa\n")
        main([str(f)])
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "noqa" in captured.out.lower()


def test_truncation_notice_when_many_violations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When violations exceed the display limit, a truncation notice should appear."""
    overflow = _MAX_VIOLATIONS_PER_PATTERN + 5
    lines = [f"x{i} = 1  # noqa: E501\n" for i in range(overflow)]
    f = tmp_path / "many.py"
    f.write_text("".join(lines))
    with patch("guardrails.hooks.suppress_comments._is_test_file", return_value=False):
        main([str(f)])
    captured = capsys.readouterr()
    assert "and 5 more" in captured.out
    assert f"showing first {_MAX_VIOLATIONS_PER_PATTERN}" in captured.out


def test_no_truncation_notice_under_limit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When violations are under the limit, no truncation notice should appear."""
    lines = [f"x{i} = 1  # noqa: E501\n" for i in range(3)]
    f = tmp_path / "few.py"
    f.write_text("".join(lines))
    with patch("guardrails.hooks.suppress_comments._is_test_file", return_value=False):
        main([str(f)])
    captured = capsys.readouterr()
    assert "more" not in captured.out


class TestMainTestFileSkipping:
    """Test that test files are correctly skipped by main()."""

    def test_test_files_are_skipped(self, tmp_path: Path) -> None:
        """Files detected as test files should be skipped."""
        f = tmp_path / "test_foo.py"
        f.write_text("x = 1  # noqa: E501\n")
        with patch("guardrails.hooks.suppress_comments._is_test_file", return_value=True):
            assert main([str(f)]) == 0
