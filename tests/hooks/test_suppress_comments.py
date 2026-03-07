"""Tests for suppress_comments hook."""

from __future__ import annotations

from ai_guardrails.hooks.suppress_comments import (
    _infer_extension,
    _is_allowlisted,
    _is_test_file,
    _load_allowlist,
    main,
)

# ---------------------------------------------------------------------------
# _is_test_file
# ---------------------------------------------------------------------------


def test_is_test_file_path_segment():
    assert _is_test_file("/project/tests/test_foo.py") is True


def test_is_test_file_test_prefix():
    assert _is_test_file("/project/src/test_auth.py") is True


def test_is_test_file_test_suffix():
    assert _is_test_file("/project/src/auth_test.py") is True


def test_is_test_file_spec_suffix():
    assert _is_test_file("/project/src/auth.spec.ts") is True


def test_is_test_file_normal_file():
    assert _is_test_file("/project/src/auth.py") is False


def test_is_test_file_dunder_tests():
    assert _is_test_file("/project/__tests__/auth.test.ts") is True


def test_is_test_file_windows_path():
    """Windows backslash paths should still detect test directories."""
    assert _is_test_file("C:\\project\\tests\\test_foo.py") is True
    assert _is_test_file("C:\\project\\__tests__\\foo.spec.js") is True
    assert _is_test_file("C:\\project\\src\\main.py") is False


# ---------------------------------------------------------------------------
# _infer_extension
# ---------------------------------------------------------------------------


def test_infer_extension_normal(tmp_path):
    f = tmp_path / "foo.py"
    f.write_text("")
    assert _infer_extension(str(f)) == "py"


def test_infer_extension_ts(tmp_path):
    f = tmp_path / "foo.ts"
    f.write_text("")
    assert _infer_extension(str(f)) == "ts"


def test_infer_extension_no_extension_shebang_bash(tmp_path):
    f = tmp_path / "myscript"
    f.write_text("#!/bin/bash\necho hi\n")
    assert _infer_extension(str(f)) in ("bash", "sh")


def test_infer_extension_no_extension_no_shebang(tmp_path):
    f = tmp_path / "myscript"
    f.write_text("echo hi\n")
    assert _infer_extension(str(f)) is None


# ---------------------------------------------------------------------------
# _load_allowlist
# ---------------------------------------------------------------------------


def test_load_allowlist_empty(tmp_path):
    result = _load_allowlist(str(tmp_path / "nonexistent"))
    assert result == []


def test_load_allowlist_reads_patterns(tmp_path):
    al = tmp_path / ".suppression-allowlist"
    al.write_text("# comment\nsome_pattern\nanother_pattern\n")
    result = _load_allowlist(str(al))
    assert result == ["some_pattern", "another_pattern"]


def test_load_allowlist_skips_blank_lines(tmp_path):
    al = tmp_path / ".suppression-allowlist"
    al.write_text("\npattern1\n\npattern2\n")
    result = _load_allowlist(str(al))
    assert result == ["pattern1", "pattern2"]


# ---------------------------------------------------------------------------
# _is_allowlisted
# ---------------------------------------------------------------------------


def test_is_allowlisted_matches():
    assert _is_allowlisted("foo.py:10:# noqa: E501", ["noqa: E501"]) is True


def test_is_allowlisted_no_match():
    assert _is_allowlisted("foo.py:10:# noqa: E501", ["noqa: E999"]) is False


def test_is_allowlisted_empty_list():
    assert _is_allowlisted("foo.py:10:# noqa", []) is False


def test_is_allowlisted_invalid_regex_skipped():
    # Invalid regex should not raise, just be skipped
    assert _is_allowlisted("foo.py:10:# noqa", ["[invalid"]) is False


# ---------------------------------------------------------------------------
# main() — integration
# ---------------------------------------------------------------------------


def test_main_no_files_returns_zero():
    assert main([]) == 0


def test_main_clean_file_returns_zero(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text("def foo():\n    pass\n")
    assert main([str(f)]) == 0


def test_main_python_noqa_returns_one(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("import os  # noqa: F401\n")
    assert main([str(f)]) == 1


def test_main_python_type_ignore_returns_one(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("x: int = 'oops'  # type: ignore\n")
    assert main([str(f)]) == 1


def test_main_typescript_ts_ignore_returns_one(tmp_path):
    f = tmp_path / "bad.ts"
    f.write_text("// @ts-ignore\nconst x = 1;\n")
    assert main([str(f)]) == 1


def test_main_test_file_skipped(tmp_path):
    f = tmp_path / "test_bad.py"
    f.write_text("import os  # noqa: F401\n")
    assert main([str(f)]) == 0


def test_main_allowlisted_suppression_skipped(tmp_path):
    f = tmp_path / "src.py"
    f.write_text("import os  # noqa: F401\n")
    al = tmp_path / ".suppression-allowlist"
    al.write_text("noqa: F401\n")
    assert main([str(f)], allowlist_path=str(al)) == 0


def test_main_nonexistent_file_skipped(tmp_path):
    missing = str(tmp_path / "nonexistent_file.py")
    assert main([missing]) == 0


def test_main_prints_error_on_violation(tmp_path, capsys):
    f = tmp_path / "bad.py"
    f.write_text("import os  # noqa: F401\n")
    main([str(f)])
    captured = capsys.readouterr()
    assert "noqa" in captured.out.lower() or "suppression" in captured.out.lower()
