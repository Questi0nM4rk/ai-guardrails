---
name: new-language
description: Language plugin author for ai-guardrails. Activates when adding support
  for a new programming language to ai-guardrails.
---

# new-language skill

I am a language plugin author. I add support for languages to ai-guardrails by
creating self-contained plugin files. Each plugin is one file, one class, fully
tested before it exists.

---

## Iron Laws

Non-negotiable. No exceptions.

1. Write `tests/test_v1/languages/test_{key}.py` BEFORE writing the plugin.
2. Everything lives in one file — detection, config generation, hook YAML all in
   `src/ai_guardrails/languages/{key}.py`.
3. Hook config is a `_HOOKS_YAML` string embedded in the class — no external template
   files.
4. Register by adding `{Key}Plugin` to `_CORE_PLUGINS` in
   `src/ai_guardrails/languages/_registry.py` — one line.
5. If a base config file is needed (for generated output), add it to
   `src/ai_guardrails/_data/configs/`.
6. Run `uv run pytest tests/test_v1/ -v` before declaring done — all tests must pass.
7. `from __future__ import annotations` is the first line of every `.py` file.
8. Max 200 lines per module — split into helpers if larger.

---

## TDD Workflow

## Step 1: Write the test file (RED)

Create `tests/test_v1/languages/test_{key}.py` with at minimum:

```python
"""Tests for {Key}Plugin."""

from __future__ import annotations

from pathlib import Path

from ai_guardrails.languages.{key} import {Key}Plugin
from ai_guardrails.models.registry import ExceptionRegistry


def _empty_registry() -> ExceptionRegistry:
    return ExceptionRegistry.from_toml(
        {
            "schema_version": 1,
            "global_rules": {},
            "exceptions": [],
            "file_exceptions": [],
            "custom": {},
            "inline_suppressions": [],
        }
    )


def test_{key}_plugin_key(tmp_path: Path) -> None:
    assert {Key}Plugin(tmp_path).key == "{key}"


def test_{key}_plugin_name(tmp_path: Path) -> None:
    assert {Key}Plugin(tmp_path).name == "{Name}"


def test_{key}_detect_when_lang_present(tmp_path: Path) -> None:
    (tmp_path / "{marker_file}").write_text("...")
    assert {Key}Plugin(tmp_path).detect(tmp_path) is True


def test_{key}_detect_false_for_unrelated(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    assert {Key}Plugin(tmp_path).detect(tmp_path) is False


def test_{key}_hook_config_has_{main_command}(tmp_path: Path) -> None:
    config = {Key}Plugin(tmp_path).hook_config()
    commands = config["pre-commit"]["commands"]
    assert "{main_command}" in commands
```

If the plugin generates config files, also add:

```python
def _make_data_dir(tmp_path: Path) -> Path:
    """Create a minimal _data/configs/ for this plugin's base config."""
    data_dir = tmp_path / "data"
    (data_dir / "configs").mkdir(parents=True)
    # Write the base config content expected by the plugin
    (data_dir / "configs" / "{config_file}").write_text("...")
    return data_dir


def test_{key}_generate_returns_config_file(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = {Key}Plugin(data_dir)
    project = tmp_path / "project"
    project.mkdir()
    outputs = plugin.generate(_empty_registry(), project)
    assert project / "{config_file}" in outputs


def test_{key}_check_missing_returns_issue(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = {Key}Plugin(data_dir)
    project = tmp_path / "project"
    project.mkdir()
    issues = plugin.check(_empty_registry(), project)
    assert len(issues) == 1
    assert "{config_file}" in issues[0]


def test_{key}_check_stale_returns_issue(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = {Key}Plugin(data_dir)
    project = tmp_path / "project"
    project.mkdir()
    (project / "{config_file}").write_text("stale content without hash header\n")
    issues = plugin.check(_empty_registry(), project)
    assert len(issues) == 1


def test_{key}_check_passes_when_fresh(tmp_path: Path) -> None:
    data_dir = _make_data_dir(tmp_path)
    plugin = {Key}Plugin(data_dir)
    project = tmp_path / "project"
    project.mkdir()
    outputs = plugin.generate(_empty_registry(), project)
    for path, content in outputs.items():
        path.write_text(content)
    issues = plugin.check(_empty_registry(), project)
    assert issues == []
```

## Step 2: Run tests — they must FAIL (expected ImportError)

```bash
uv run pytest tests/test_v1/languages/test_{key}.py -v
```

Expected: `ModuleNotFoundError: No module named 'ai_guardrails.languages.{key}'`

If tests pass: the plugin already exists or the test is wrong. Stop and investigate.

## Step 3: Create the plugin

Create `src/ai_guardrails/languages/{key}.py` (see template below).

## Step 4: Run tests — they must PASS

```bash
uv run pytest tests/test_v1/languages/test_{key}.py -v
```

All tests must pass. If any fail, fix the plugin (NOT the tests).

## Step 5: Register the plugin

Add one line to `src/ai_guardrails/languages/_registry.py`:

```python
from ai_guardrails.languages.{key} import {Key}Plugin

_CORE_PLUGINS: list[type[BaseLanguagePlugin]] = [
    UniversalPlugin,
    PythonPlugin,
    # ... existing plugins ...
    {Key}Plugin,   # <-- add here, alphabetical or logical order
]
```

## Step 6: Run full test suite

```bash
uv run pytest tests/test_v1/ -v
```

All existing tests must still pass. No regressions.

## Step 7: Lint clean

```bash
uv run ruff check src/ai_guardrails/
```

Zero errors.

---

## Plugin Template

## Minimal plugin (detect + hooks only, no generated configs)

```python
"""${Key}Plugin — detects ${Name} projects."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_guardrails.languages._base import BaseLanguagePlugin


class ${Key}Plugin(BaseLanguagePlugin):
    """Language plugin for ${Name} projects."""

    key = "${key}"
    name = "${Name}"
    detect_files = ["${marker_file}"]   # exact files in project root
    detect_patterns = ["*.${ext}"]       # glob patterns (searched recursively)
    detect_dirs: list[str] = []          # subdirectory names (e.g., ["lua"])
    copy_files: list[str] = []           # files to copy from _data/configs/
    generated_configs: list[str] = []    # files this plugin generates

    _HOOKS_YAML = """\
pre-commit:
  commands:
    ${key}-format-and-stage:
      glob: "*.${ext}"
      run: ${formatter} {staged_files} && git add {staged_files}
      stage_fixed: true
      priority: 1
    ${key}-lint:
      glob: "*.${ext}"
      run: ${linter} {staged_files}
      priority: 2
"""

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        """Return ${Name} pre-commit hooks config."""
        return yaml.safe_load(self._HOOKS_YAML) or {}
```

## Plugin with generated config

When the plugin produces a config file with hash protection, also implement
`generate()` and `check()`:

```python
"""${Key}Plugin — detects ${Name}, generates ${config_file}."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from ai_guardrails.generators.base import HASH_HEADER_PREFIX, compute_hash, verify_hash
from ai_guardrails.languages._base import BaseLanguagePlugin

if TYPE_CHECKING:
    from ai_guardrails.models.registry import ExceptionRegistry


class ${Key}Plugin(BaseLanguagePlugin):
    """Language plugin for ${Name} projects."""

    key = "${key}"
    name = "${Name}"
    detect_files = ["${marker_file}"]
    detect_patterns = ["*.${ext}"]
    detect_dirs: list[str] = []
    copy_files: list[str] = []
    generated_configs = ["${config_file}"]

    _HOOKS_YAML = """\
pre-commit:
  commands:
    ${key}-format-and-stage:
      glob: "*.${ext}"
      run: ${formatter} {staged_files} && git add {staged_files}
      stage_fixed: true
      priority: 1
    ${key}-lint:
      glob: "*.${ext}"
      run: ${linter} {staged_files}
      priority: 2
"""

    def __init__(self, data_dir: Path) -> None:
        self._configs_dir = data_dir / "configs"

    def _load_base(self) -> str:
        src = self._configs_dir / "${config_file}"
        if not src.exists():
            raise FileNotFoundError(src)
        return src.read_text()

    def _build_body(self, registry: ExceptionRegistry) -> str:  # noqa: ARG002
        """Build config body from base template + registry exceptions."""
        base = self._load_base()
        # Apply registry exceptions here if the format supports it
        return base

    def generate(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> dict[Path, str]:
        """Return {project_dir/${config_file}: content_with_hash_header}."""
        body = self._build_body(registry)
        header = f"{HASH_HEADER_PREFIX}{compute_hash(body)}"
        full_content = f"{header}\n{body}"
        return {project_dir / "${config_file}": full_content}

    def hook_config(self) -> dict:  # type: ignore[type-arg]
        """Return ${Name} pre-commit hooks config."""
        return yaml.safe_load(self._HOOKS_YAML) or {}

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return issues if ${config_file} is missing or stale."""
        target = project_dir / "${config_file}"
        if not target.exists():
            return ["${config_file} is missing — run: ai-guardrails generate"]
        existing = target.read_text()
        try:
            expected_body = self._build_body(registry)
        except FileNotFoundError:
            return ["${config_file} base config not found in package data"]
        if not verify_hash(existing, expected_body):
            return ["${config_file} is stale or tampered — run: ai-guardrails generate"]
        return []
```

---

## Base config files

If the plugin needs a base config (`copy_files` or for `generate()`), add the file to:

```
src/ai_guardrails/_data/configs/{config_file}
```

Rules for base configs:
- Enable ALL rules / strictest settings available
- Document the tool and version in a comment header
- No project-specific exceptions — those come from the exception registry

---

## Suppression patterns

If the language has linter-disable inline comments, add them to
`SUPPRESSION_PATTERNS` in `src/ai_guardrails/constants.py`:

```python
# ${Name}
(r"${suppression_pattern}", "${description}", frozenset({"${ext}"})),
```

Examples already present: `# noqa` (Python), `//nolint` (Go), `# shellcheck disable` (Shell).

---

## User/local plugins

For project-specific languages not in core, drop `{key}.py` in
`~/.ai-guardrails/plugins/`. No registration needed — `discover_plugins()` loads
all `*.py` files from that directory automatically.

Same interface as core plugins: subclass `BaseLanguagePlugin`, set class attributes,
implement `hook_config()`. The plugin will never be overwritten by package updates.

---

## Checklist

Before marking a language PR complete:

- [ ] `tests/test_v1/languages/test_{key}.py` written first (TDD red)
- [ ] `src/ai_guardrails/languages/{key}.py` implemented (TDD green)
- [ ] `_CORE_PLUGINS` in `_registry.py` updated
- [ ] Base config in `_data/configs/` if needed
- [ ] Suppression patterns in `constants.py` if language has inline suppressions
- [ ] `uv run pytest tests/test_v1/ -v` — all pass
- [ ] `uv run ruff check src/ai_guardrails/` — zero errors
- [ ] `from __future__ import annotations` is the first line of every new file
- [ ] Plugin is under 200 lines
